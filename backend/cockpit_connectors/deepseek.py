"""Connecteur DeepSeek — GET /user/balance."""

from __future__ import annotations

import logging
from typing import Any

from cockpit_connectors._helpers import (
    build_usage_payload,
    http_get_json,
    transactions_usage,
    usd_to_eur,
)
from cockpit_connectors.base import BaseConnector
from security.secret_encoding import secret_for_http_header

logger = logging.getLogger(__name__)

_BALANCE_URL = "https://api.deepseek.com/user/balance"


class DeepSeekConnector(BaseConnector):
    def _auth_headers(self) -> dict[str, str]:
        token = secret_for_http_header(self.api_key)
        if token.lower().startswith("bearer "):
            token = token[7:].strip()
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json; charset=utf-8",
        }

    def get_balance(self) -> float:
        if not self.api_key:
            return self._cached_balance()

        data, err = http_get_json(_BALANCE_URL, headers=self._auth_headers())
        if err or not data:
            logger.debug("DeepSeek balance API: %s — repli SQLite", err)
            return self._cached_balance()

        infos = data.get("balance_infos") or []
        if not isinstance(infos, list):
            return self._cached_balance()

        for info in infos:
            if not isinstance(info, dict):
                continue
            currency = str(info.get("currency") or "USD").upper()
            try:
                total = float(info.get("total_balance") or 0)
            except (TypeError, ValueError):
                continue
            if currency == "EUR":
                return round(total, 8)
            return usd_to_eur(total)

        return self._cached_balance()

    def get_usage(self) -> dict[str, Any]:
        items = transactions_usage(self.service_id)
        if not self.api_key:
            return self._usage_from_cache(error="DEEPSEEK_API_KEY absente")

        data, err = http_get_json(_BALANCE_URL, headers=self._auth_headers())
        extra: dict[str, Any] = {}
        if isinstance(data, dict):
            extra["is_available"] = data.get("is_available")
            extra["balance_infos"] = data.get("balance_infos")

        source = "api" if not err else "cache"
        total = self.get_balance() if not err else 0.0
        return build_usage_payload(
            source=source,
            service_id=self.service_id,
            total_eur=total,
            items=items,
            extra=extra,
            error=err,
        )

    def ping(self) -> bool:
        if not self.api_key:
            return False
        data, err = http_get_json(_BALANCE_URL, headers=self._auth_headers(), timeout=10.0)
        if err:
            return False
        if isinstance(data, dict) and data.get("is_available") is False:
            return False
        return True

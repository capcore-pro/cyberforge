"""Connecteur Tavily — GET /usage (crédits plan)."""

from __future__ import annotations

import logging
from typing import Any

from cockpit_connectors._helpers import (
    build_usage_payload,
    http_get_json,
    transactions_usage,
)
from cockpit_connectors.base import BaseConnector

logger = logging.getLogger(__name__)

_USAGE_URL = "https://api.tavily.com/usage"
_CREDIT_EUR = 0.008 * 0.92  # ~0.00736 EUR par crédit (estimation)


class TavilyConnector(BaseConnector):
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _fetch_usage(self) -> tuple[dict[str, Any] | None, str | None]:
        return http_get_json(_USAGE_URL, headers=self._headers(), timeout=15.0)

    def _credits_to_eur(self, used: int, limit: int | None) -> tuple[float, float]:
        used_eur = round(used * _CREDIT_EUR, 8)
        if limit is None or limit <= 0:
            return used_eur, self._cached_balance()
        remaining_credits = max(0, limit - used)
        remaining_eur = round(remaining_credits * _CREDIT_EUR, 8)
        return used_eur, remaining_eur

    def get_balance(self) -> float:
        if not self.api_key:
            return self._cached_balance()

        data, err = self._fetch_usage()
        if err or not data:
            logger.debug("Tavily usage API: %s — repli SQLite", err)
            return self._cached_balance()

        key_block = data.get("key") if isinstance(data.get("key"), dict) else data
        try:
            used = int(key_block.get("usage") or 0)
        except (TypeError, ValueError):
            used = 0
        limit_raw = key_block.get("limit")
        limit = int(limit_raw) if limit_raw is not None else None
        _, remaining_eur = self._credits_to_eur(used, limit)
        return remaining_eur

    def get_usage(self) -> dict[str, Any]:
        items = transactions_usage(self.service_id)
        if not self.api_key:
            return self._usage_from_cache(error="TAVILY_API_KEY absente")

        data, err = self._fetch_usage()
        extra: dict[str, Any] = {}
        total_spent = 0.0
        if isinstance(data, dict):
            key_block = data.get("key") if isinstance(data.get("key"), dict) else data
            extra["usage"] = key_block
            try:
                used = int(key_block.get("usage") or 0)
            except (TypeError, ValueError):
                used = 0
            limit_raw = key_block.get("limit")
            limit = int(limit_raw) if limit_raw is not None else None
            total_spent, _ = self._credits_to_eur(used, limit)

        return build_usage_payload(
            source="api" if not err else "cache",
            service_id=self.service_id,
            total_eur=total_spent,
            items=items,
            extra=extra,
            error=err,
        )

    def ping(self) -> bool:
        if not self.api_key:
            return False
        _, err = http_get_json(_USAGE_URL, headers=self._headers(), timeout=12.0)
        return err is None

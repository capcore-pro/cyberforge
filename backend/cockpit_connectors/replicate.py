"""Connecteur Replicate — pas de solde API public ; repli SQLite + cost_tracker."""

from __future__ import annotations

import logging
from typing import Any

from cockpit_connectors._helpers import (
    build_usage_payload,
    cost_tracker_spent_eur,
    http_get_json,
    transactions_usage,
)
from cockpit_connectors.base import BaseConnector

logger = logging.getLogger(__name__)

_ACCOUNT_URL = "https://api.replicate.com/v1/account"


class ReplicateConnector(BaseConnector):
    def _auth_headers(self) -> dict[str, str]:
        token = self.api_key
        if not token.lower().startswith("bearer "):
            token = f"Bearer {token}"
        return {
            "Authorization": token,
            "Content-Type": "application/json",
        }

    def get_balance(self) -> float:
        return self._cached_balance()

    def get_usage(self) -> dict[str, Any]:
        items = transactions_usage(self.service_id)
        spent = cost_tracker_spent_eur(self.service_id)
        extra: dict[str, Any] = {}

        if self.api_key:
            data, err = http_get_json(_ACCOUNT_URL, headers=self._auth_headers())
            if data:
                extra["account"] = {
                    "type": data.get("type"),
                    "username": data.get("username"),
                    "name": data.get("name"),
                }
            return build_usage_payload(
                source="cost_tracker" if spent else "cache",
                service_id=self.service_id,
                total_eur=spent,
                items=items,
                extra=extra,
                error=err,
            )

        return self._usage_from_cache(error="REPLICATE_API_KEY absente")

    def ping(self) -> bool:
        if not self.api_key:
            return False
        _, err = http_get_json(_ACCOUNT_URL, headers=self._auth_headers(), timeout=12.0)
        return err is None

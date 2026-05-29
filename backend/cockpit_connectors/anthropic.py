"""Connecteur Anthropic — crédits prépayés ou repli cost_tracker / SQLite."""

from __future__ import annotations

import logging
import os
from typing import Any

from cockpit_connectors._helpers import (
    build_usage_payload,
    cost_tracker_spent_eur,
    http_get_json,
    http_post_json,
    transactions_usage,
)
from cockpit_connectors.base import BaseConnector

logger = logging.getLogger(__name__)

_API_BASE = "https://api.anthropic.com"
_HAIKU_MODEL = "claude-3-5-haiku-20241022"


class AnthropicConnector(BaseConnector):
    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    def _fetch_prepaid_credits_eur(self) -> float | None:
        org_id = (os.environ.get("ANTHROPIC_ORG_ID") or "").strip()
        if not org_id:
            return None
        url = f"https://console.anthropic.com/api/organizations/{org_id}/prepaid/credits"
        data, err = http_get_json(url, headers=self._headers(), timeout=12.0)
        if err or not data:
            logger.debug("Anthropic prepaid credits indisponible: %s", err)
            return None
        amount = data.get("amount")
        if amount is None:
            return None
        try:
            return round(float(amount) / 100.0, 4)
        except (TypeError, ValueError):
            return None

    def get_balance(self) -> float:
        if not self.api_key:
            return self._cached_balance()

        prepaid = self._fetch_prepaid_credits_eur()
        if prepaid is not None:
            return prepaid

        spent = cost_tracker_spent_eur(self.service_id)
        if spent > 0:
            return max(0.0, round(self._cached_balance() - spent, 8))

        return self._cached_balance()

    def get_usage(self) -> dict[str, Any]:
        items = transactions_usage(self.service_id)
        spent = cost_tracker_spent_eur(self.service_id)
        if not self.api_key:
            return self._usage_from_cache(error="ANTHROPIC_API_KEY absente")

        _, err = http_get_json(
            f"{_API_BASE}/v1/organizations",
            headers=self._headers(),
            timeout=10.0,
        )
        source = "api" if not err else "cost_tracker"
        return build_usage_payload(
            source=source,
            service_id=self.service_id,
            total_eur=spent,
            items=items,
            error=err,
        )

    def ping(self) -> bool:
        if not self.api_key:
            return False
        body = {
            "model": _HAIKU_MODEL,
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "ping"}],
        }
        _, status, err = http_post_json(
            f"{_API_BASE}/v1/messages",
            headers=self._headers(),
            body=body,
            timeout=25.0,
        )
        if err:
            logger.debug("Anthropic ping échoué: %s", err)
            return False
        return status < 400

"""Connecteur manuel — solde géré dans SQLite (pas de sync billing API)."""

from __future__ import annotations

import logging
from typing import Any

from cockpit_connectors._helpers import build_usage_payload, transactions_usage
from cockpit_connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class ManualConnector(BaseConnector):
    """Railway, Vercel, Brevo, GitHub, Unsplash, Cloudflare, v0, etc."""

    def get_balance(self) -> float:
        return self._cached_balance()

    def get_usage(self) -> dict[str, Any]:
        items = transactions_usage(self.service_id)
        spent = sum(
            row["amount_eur"]
            for row in items
            if row.get("type") == "expense"
        )
        return build_usage_payload(
            source="manual",
            service_id=self.service_id,
            total_eur=spent,
            items=items,
            extra={"note": "Solde et transactions gérés manuellement dans le cockpit."},
        )

    def ping(self) -> bool:
        return True

"""Classe de base des connecteurs cockpit."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from security.secret_encoding import secret_for_http_header

from . import _helpers


class BaseConnector(ABC):
    """Connecteur fournisseur — solde, usage et disponibilité."""

    def __init__(self, service_id: str, api_key: str) -> None:
        self.service_id = service_id.strip()
        self.api_key = secret_for_http_header(api_key)

    @abstractmethod
    def get_balance(self) -> float:
        """Solde restant en EUR."""

    @abstractmethod
    def get_usage(self) -> dict[str, Any]:
        """Dépenses / usage récents (dict sérialisable)."""

    @abstractmethod
    def ping(self) -> bool:
        """True si le service répond."""

    def _cached_balance(self) -> float:
        return _helpers.cached_balance_eur(self.service_id)

    def _usage_from_cache(self, *, error: str | None = None) -> dict[str, Any]:
        return _helpers.build_usage_payload(
            source="cache",
            service_id=self.service_id,
            total_eur=_helpers.cost_tracker_spent_eur(self.service_id),
            items=_helpers.transactions_usage(self.service_id),
            error=error,
        )

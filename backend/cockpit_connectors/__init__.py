"""
Registre des connecteurs cockpit — sync soldes et usage fournisseurs.

Usage::

    from cockpit_connectors import get_connector

    connector = get_connector("anthropic", api_key)
    if connector:
        balance = connector.get_balance()
"""

from __future__ import annotations

from typing import Type

from cockpit_connectors.anthropic import AnthropicConnector
from cockpit_connectors.base import BaseConnector
from cockpit_connectors.deepseek import DeepSeekConnector
from cockpit_connectors.manual import ManualConnector
from cockpit_connectors.replicate import ReplicateConnector
from cockpit_connectors.tavily import TavilyConnector

CONNECTORS: dict[str, Type[BaseConnector]] = {
    "anthropic": AnthropicConnector,
    "deepseek": DeepSeekConnector,
    "replicate": ReplicateConnector,
    "tavily": TavilyConnector,
    "manual": ManualConnector,
    # Fournisseurs sans API billing — solde SQLite manuel
    "v0": ManualConnector,
    "railway": ManualConnector,
    "vercel": ManualConnector,
    "cloudflare": ManualConnector,
    "brevo": ManualConnector,
    "github": ManualConnector,
    "unsplash": ManualConnector,
}


def get_connector(
    name: str,
    api_key: str,
    *,
    service_id: str | None = None,
) -> BaseConnector | None:
    """
    Instancie le connecteur nommé (champ ``connector`` du service cockpit).

    ``service_id`` : id SQLite du service (défaut = ``name``). Utile quand le type
    connecteur diffère de l'id (ex. ``get_connector("manual", key, service_id="railway")``).

    Retourne ``None`` si aucun connecteur n'est enregistré (pas de sync automatique).
    """
    key = (name or "").strip().lower()
    if not key:
        return None
    cls = CONNECTORS.get(key)
    if cls is None:
        return None
    sid = (service_id or name).strip()
    if not sid:
        return None
    return cls(service_id=sid, api_key=api_key or "")


__all__ = [
    "CONNECTORS",
    "AnthropicConnector",
    "BaseConnector",
    "DeepSeekConnector",
    "ManualConnector",
    "ReplicateConnector",
    "TavilyConnector",
    "get_connector",
]

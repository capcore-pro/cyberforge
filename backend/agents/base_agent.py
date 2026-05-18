"""
Classe de base pour les agents IA CyberForge.
Les clés API sont injectées via Settings, jamais en dur dans le code.
"""

from abc import ABC, abstractmethod
from typing import Any

from config import Settings, get_settings


class BaseAgent(ABC):
    """Contrat commun à tous les agents (analyse, reconnaissance, rapport, etc.)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    @abstractmethod
    def agent_id(self) -> str:
        """Identifiant unique de l'agent."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Nom affiché de l'agent."""

    def has_llm_credentials(self) -> bool:
        """
        Indique si au moins un fournisseur LLM est configuré via l'environnement.
        Ne expose pas la valeur des clés.
        """
        openai = self._settings.openai_api_key
        anthropic = self._settings.anthropic_api_key
        ollama = self._settings.ollama_base_url
        return bool(
            (openai and openai.get_secret_value())
            or (anthropic and anthropic.get_secret_value())
            or ollama
        )

    @abstractmethod
    async def run(self, prompt: str, **kwargs: Any) -> str:
        """Exécute une tâche agentique à partir d'un prompt utilisateur."""

"""
Configuration centralisée — chargée depuis les variables d'environnement.
Les clés API ne sont jamais codées en dur dans le dépôt.
"""

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Charge .env à la racine du monorepo (parent de backend/)
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")


class Settings(BaseSettings):
    """Paramètres applicatifs lus depuis l'environnement."""

    model_config = SettingsConfigDict(
        env_file=_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="CyberForge", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=False, alias="APP_DEBUG")

    backend_host: str = Field(default="127.0.0.1", alias="BACKEND_HOST")
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")

    database_url: str = Field(default="sqlite:///./database/cyberforge.db", alias="DATABASE_URL")

    # SecretStr empêche l'affichage accidentel des clés dans les logs
    openai_api_key: SecretStr | None = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: SecretStr | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    coremind_claude_model: str = Field(
        default="claude-sonnet-4-20250514",
        alias="COREMIND_CLAUDE_MODEL",
        description="Modèle Claude pour la génération de code CoreMindAI",
    )
    ollama_base_url: str | None = Field(default=None, alias="OLLAMA_BASE_URL")

    secret_key: SecretStr = Field(default=SecretStr("change-me-in-production"), alias="SECRET_KEY")
    cors_origins: str = Field(
        default="http://127.0.0.1:5173,http://localhost:5173",
        alias="CORS_ORIGINS",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        """Liste des origines CORS autorisées."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Instance singleton des paramètres (mise en cache)."""
    return Settings()

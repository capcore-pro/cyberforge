"""
Configuration centralisée — chargée depuis les variables d'environnement.
Les clés API ne sont jamais codées en dur dans le dépôt.
"""

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = Path(__file__).resolve().parent


def load_env_files() -> None:
    """
    Charge les fichiers .env dans os.environ.
    backend/.env écrase la racine (override) pour que SUPABASE_* soit bien lu.
    """
    load_dotenv(_ROOT / ".env")
    load_dotenv(_BACKEND / ".env", override=True)


load_env_files()


class Settings(BaseSettings):
    """Paramètres applicatifs lus depuis l'environnement."""

    model_config = SettingsConfigDict(
        env_file=(_ROOT / ".env", _BACKEND / ".env"),
        env_file_encoding="utf-8",
        # Sinon des SUPABASE_*="" dans l'environnement masquent backend/.env
        env_ignore_empty=True,
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = Field(default="CyberForge", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=False, alias="APP_DEBUG")

    backend_host: str = Field(default="127.0.0.1", alias="BACKEND_HOST")
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")

    database_url: str = Field(default="sqlite:///./database/cyberforge.db", alias="DATABASE_URL")

    openai_api_key: SecretStr | None = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: SecretStr | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    deepseek_api_key: SecretStr | None = Field(default=None, alias="DEEPSEEK_API_KEY")
    google_generative_ai_api_key: SecretStr | None = Field(
        default=None, alias="GOOGLE_GENERATIVE_AI_API_KEY"
    )
    ollama_base_url: str | None = Field(default=None, alias="OLLAMA_BASE_URL")

    coremind_deepseek_model: str = Field(
        default="deepseek-chat", alias="COREMIND_DEEPSEEK_MODEL"
    )
    coremind_gemini_model: str = Field(
        default="gemini-2.0-flash", alias="COREMIND_GEMINI_MODEL"
    )
    coremind_haiku_model: str = Field(
        default="claude-3-5-haiku-20241022", alias="COREMIND_HAIKU_MODEL"
    )
    coremind_sonnet_model: str = Field(
        default="claude-sonnet-4-20250514", alias="COREMIND_SONNET_MODEL"
    )
    coremind_llm_timeout_seconds: float = Field(
        default=30.0, alias="COREMIND_LLM_TIMEOUT_SECONDS"
    )
    coremind_max_output_tokens: int = Field(
        default=2048, alias="COREMIND_MAX_OUTPUT_TOKENS"
    )
    coremind_max_provider_attempts: int = Field(
        default=2, alias="COREMIND_MAX_PROVIDER_ATTEMPTS"
    )

    supabase_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SUPABASE_URL", "supabase_url"),
    )
    supabase_anon_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("SUPABASE_ANON_KEY", "supabase_anon_key"),
    )
    supabase_secret_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "SUPABASE_SECRET_KEY",
            "SUPABASE_SERVICE_ROLE_KEY",
            "SUPABASE_SERVICE_KEY",
        ),
    )

    secret_key: SecretStr = Field(default=SecretStr("change-me-in-production"), alias="SECRET_KEY")

    cors_origins: str = Field(
        default="http://127.0.0.1:5173,http://localhost:5173",
        alias="CORS_ORIGINS",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        """Liste des origines CORS autorisées."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def supabase_configured(self) -> bool:
        """True si le backend peut écrire dans Supabase (URL + clé secrète)."""
        return bool(self.supabase_url and self.supabase_url.strip() and self.supabase_service_key)

    @property
    def supabase_service_key(self) -> str:
        """Clé service_role / secret pour PostgREST (jamais exposée au frontend)."""
        if self.supabase_secret_key is None:
            return ""
        return self.supabase_secret_key.get_secret_value().strip()

    @field_validator("supabase_url", mode="before")
    @classmethod
    def _strip_supabase_url(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().strip('"').strip("'")
        return value


@lru_cache
def get_settings() -> Settings:
    """Instance singleton des paramètres (mise en cache)."""
    return Settings()


def refresh_settings() -> Settings:
    """Recharge les .env et invalide le cache (démarrage / tests)."""
    load_env_files()
    get_settings.cache_clear()
    return get_settings()

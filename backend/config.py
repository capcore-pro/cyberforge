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


def plain_secret_str(value: SecretStr | str | None) -> str:
    """Extrait une chaîne utilisable depuis un SecretStr pydantic."""
    if value is None:
        return ""
    if isinstance(value, SecretStr):
        return value.get_secret_value().strip()
    return str(value).strip()


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
    backend_port: int = Field(default=8002, alias="BACKEND_PORT")
    backend_url_env: str | None = Field(default=None, alias="BACKEND_URL")
    demo_api_base_url: str = Field(
        default="https://cyberforge-backend-production.up.railway.app",
        alias="DEMO_API_BASE_URL",
        description="URL API injectée dans les démos Cloudflare (formulaire CapCore).",
    )

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

    v0_api_key: SecretStr | None = Field(default=None, alias="V0_API_KEY")
    v0_api_base_url: str | None = Field(default=None, alias="V0_API_BASE_URL")
    v0_model: str | None = Field(default=None, alias="V0_MODEL")
    builder_http_timeout_seconds: float = Field(
        default=45.0, alias="BUILDER_HTTP_TIMEOUT_SECONDS"
    )
    builder_max_output_tokens: int = Field(
        default=4096, alias="BUILDER_MAX_OUTPUT_TOKENS"
    )

    replicate_api_key: SecretStr | None = Field(default=None, alias="REPLICATE_API_KEY")
    replicate_html_model: str | None = Field(
        default=None, alias="REPLICATE_HTML_MODEL"
    )
    vision_screenshot_width: int = Field(default=1280, alias="VISION_SCREENSHOT_WIDTH")
    vision_screenshot_height: int = Field(default=720, alias="VISION_SCREENSHOT_HEIGHT")
    vision_html_max_chars: int = Field(default=120_000, alias="VISION_HTML_MAX_CHARS")
    vision_replicate_timeout_seconds: float = Field(
        default=90.0, alias="VISION_REPLICATE_TIMEOUT_SECONDS"
    )
    vision_replicate_poll_seconds: float = Field(
        default=1.5, alias="VISION_REPLICATE_POLL_SECONDS"
    )

    railway_api_key: SecretStr | None = Field(default=None, alias="RAILWAY_API_KEY")
    github_token: SecretStr | None = Field(default=None, alias="GITHUB_TOKEN")
    github_repo: str | None = Field(
        default=None,
        description="owner/repo optionnel pour push de branche",
        alias="GITHUB_REPO",
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

    cloudflare_account_id: SecretStr | None = Field(
        default=None, alias="CLOUDFLARE_ACCOUNT_ID"
    )
    cloudflare_api_token: SecretStr | None = Field(
        default=None, alias="CLOUDFLARE_API_TOKEN"
    )

    capcore_notify_email: str = Field(
        default="capcore.pro@gmail.com",
        alias="CAPCORE_NOTIFY_EMAIL",
    )
    brevo_api_key: SecretStr | None = Field(default=None, alias="BREVO_API_KEY")
    brevo_sender_email: str | None = Field(
        default=None,
        alias="BREVO_SENDER_EMAIL",
        description="Expéditeur vérifié dans Brevo (défaut : CAPCORE_NOTIFY_EMAIL).",
    )
    brevo_sender_name: str = Field(default="CyberForge", alias="BREVO_SENDER_NAME")

    cors_origins: str = Field(
        default="http://127.0.0.1:5173,http://localhost:5173",
        alias="CORS_ORIGINS",
    )
    frontend_public_url_env: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "FRONTEND_PUBLIC_URL",
            "VITE_DEV_SERVER_URL",
        ),
    )

    @property
    def cors_origin_list(self) -> list[str]:
        """Liste des origines CORS autorisées."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def backend_public_url(self) -> str:
        """URL publique du backend (appels depuis les démos Cloudflare)."""
        explicit = self.backend_url_env
        if explicit and str(explicit).strip():
            return str(explicit).strip().rstrip("/")
        return f"http://{self.backend_host}:{self.backend_port}"

    @property
    def frontend_public_url(self) -> str:
        """URL de base du frontend pour les liens /demo/{token}."""
        explicit = self.frontend_public_url_env
        if explicit and str(explicit).strip():
            return str(explicit).strip().rstrip("/")
        origins = self.cors_origin_list
        if origins:
            return origins[0].rstrip("/")
        return "http://localhost:5173"

    @property
    def v0_configured(self) -> bool:
        """True si une clé v0 (Vercel) est définie."""
        return bool(plain_secret_str(self.v0_api_key))

    @property
    def replicate_configured(self) -> bool:
        """True si Replicate est configuré pour VisionUI."""
        return bool(plain_secret_str(self.replicate_api_key))

    @property
    def railway_configured(self) -> bool:
        """True si Railway est configuré pour ExportAI."""
        return bool(plain_secret_str(self.railway_api_key))

    @property
    def github_configured(self) -> bool:
        """True si un token GitHub est configuré pour ExportAI."""
        return bool(plain_secret_str(self.github_token))

    @property
    def cloudflare_configured(self) -> bool:
        """True si Account ID et token API sont définis dans backend/.env."""
        return bool(
            plain_secret_str(self.cloudflare_account_id)
            and plain_secret_str(self.cloudflare_api_token)
        )

    @property
    def supabase_configured(self) -> bool:
        """True si le backend peut écrire dans Supabase (URL + clé secrète)."""
        return bool(
            self.supabase_url
            and self.supabase_url.strip()
            and plain_secret_str(self.supabase_secret_key)
        )

    @property
    def supabase_service_key(self) -> str:
        """Clé service_role / secret pour PostgREST (jamais exposée au frontend)."""
        return plain_secret_str(self.supabase_secret_key)

    @property
    def supabase_public_key(self) -> str:
        """Clé anon / publishable pour l'en-tête apikey PostgREST."""
        return plain_secret_str(self.supabase_anon_key)

    @field_validator("supabase_url", mode="before")
    @classmethod
    def _strip_supabase_url(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().strip('"').strip("'")
        return value

    @field_validator("supabase_secret_key", "supabase_anon_key", mode="before")
    @classmethod
    def _coerce_supabase_secret(cls, value: object) -> object:
        if value is None or value == "":
            return None
        if isinstance(value, SecretStr):
            return value
        return SecretStr(plain_secret_str(value))  # type: ignore[arg-type]


@lru_cache
def get_settings() -> Settings:
    """Instance singleton des paramètres (mise en cache)."""
    return Settings()


def refresh_settings() -> Settings:
    """Recharge les .env et invalide le cache (démarrage / tests)."""
    load_env_files()
    get_settings.cache_clear()
    return get_settings()

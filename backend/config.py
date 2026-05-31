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
    load_dotenv(_ROOT / ".env", encoding="utf-8")
    load_dotenv(_BACKEND / ".env", override=True, encoding="utf-8")


load_env_files()


def plain_secret_str(value: SecretStr | str | None) -> str:
    """Extrait une chaîne utilisable depuis un SecretStr pydantic (UTF-8)."""
    from security.secret_encoding import normalize_secret_text

    if value is None:
        return ""
    if isinstance(value, SecretStr):
        return normalize_secret_text(value.get_secret_value())
    return normalize_secret_text(value)


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
        default=4,
        alias="COREMIND_MAX_PROVIDER_ATTEMPTS",
        description="Nombre max de fournisseurs LLM tentés (DeepSeek, Gemini, Sonnet…).",
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

    openhands_enabled: bool = Field(default=True, alias="OPENHANDS_ENABLED")
    openhands_use_sdk: bool = Field(
        default=True,
        alias="OPENHANDS_USE_SDK",
        description="Utiliser le SDK OpenHands si Python ≥ 3.12 ; sinon repli Anthropic direct.",
    )
    openhands_complexity_threshold: int = Field(
        default=7,
        ge=1,
        le=10,
        alias="OPENHANDS_COMPLEXITY_THRESHOLD",
    )
    openhands_timeout_seconds: float = Field(
        default=180.0, alias="OPENHANDS_TIMEOUT_SECONDS"
    )
    openhands_max_output_tokens: int = Field(
        default=8192, alias="OPENHANDS_MAX_OUTPUT_TOKENS"
    )

    playwright_enabled: bool = Field(default=True, alias="PLAYWRIGHT_ENABLED")
    playwright_pass_threshold: int = Field(
        default=70,
        ge=0,
        le=100,
        alias="PLAYWRIGHT_PASS_THRESHOLD",
    )
    playwright_timeout_seconds: float = Field(
        default=60.0, alias="PLAYWRIGHT_TIMEOUT_SECONDS"
    )

    replicate_api_key: SecretStr | None = Field(default=None, alias="REPLICATE_API_KEY")
    replicate_html_model: str | None = Field(
        default=None, alias="REPLICATE_HTML_MODEL"
    )
    replicate_image_model: str | None = Field(
        default=None,
        alias="REPLICATE_IMAGE_MODEL",
        description="Modèle Replicate text-to-image (fallback VisionUI).",
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
    railway_workspace_id: str | None = Field(
        default=None,
        alias="RAILWAY_WORKSPACE_ID",
        description="Workspace ID Railway (optionnel, requis si token n'embarque pas le workspace par défaut).",
    )
    railway_shared_project_id: str | None = Field(
        default=None,
        alias="RAILWAY_SHARED_PROJECT_ID",
        description="Project ID Railway partagé (Option C) pour réutiliser un seul projet et créer/supprimer des services dedans.",
    )
    github_token: SecretStr | None = Field(default=None, alias="GITHUB_TOKEN")
    github_repo: str | None = Field(
        default=None,
        description="owner/repo optionnel pour push de branche",
        alias="GITHUB_REPO",
    )
    vitrines_github_repo: str = Field(
        default="mathiasgibiard-dotcom/vitrines",
        alias="VITRINES_GITHUB_REPO",
        description="Dépôt GitHub — une branche par site vitrine Next.js (Vercel).",
    )
    applications_web_github_repo: str = Field(
        default="mathiasgibiard-dotcom/applications-web",
        alias="APPLICATIONS_WEB_GITHUB_REPO",
        description="Dépôt GitHub — une branche par application web (Railway + Vercel).",
    )
    vercel_token: SecretStr | None = Field(
        default=None,
        alias="VERCEL_TOKEN",
        description="Token API Vercel pour déploiement / configuration automatisée.",
    )
    vercel_team_id: str | None = Field(
        default=None,
        alias="VERCEL_TEAM_ID",
        description="Team ID Vercel (optionnel) pour scoper les appels API.",
    )
    vercel_vitrines_project_id: str | None = Field(
        default=None,
        alias="VERCEL_VITRINES_PROJECT_ID",
        description="Project ID Vercel du projet 'vitrines' (optionnel si résoluble par nom).",
    )
    vercel_vitrines_project_name: str = Field(
        default="vitrines",
        alias="VERCEL_VITRINES_PROJECT_NAME",
        description="Nom du projet Vercel vitrines (par défaut 'vitrines').",
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

    # Médiathèque — Cloudflare R2 (API S3-compatible)
    cloudflare_r2_account_id: SecretStr | None = Field(
        default=None, alias="CLOUDFLARE_R2_ACCOUNT_ID"
    )
    cloudflare_r2_access_key_id: SecretStr | None = Field(
        default=None, alias="CLOUDFLARE_R2_ACCESS_KEY_ID"
    )
    cloudflare_r2_secret_access_key: SecretStr | None = Field(
        default=None, alias="CLOUDFLARE_R2_SECRET_ACCESS_KEY"
    )
    cloudflare_r2_bucket: str | None = Field(
        default=None, alias="CLOUDFLARE_R2_BUCKET"
    )
    cloudflare_r2_public_base_url: str | None = Field(
        default=None,
        alias="CLOUDFLARE_R2_PUBLIC_BASE_URL",
        description="URL publique du bucket R2 (domaine custom ou r2.dev).",
    )
    media_root: str | None = Field(
        default=None,
        alias="MEDIA_ROOT",
        description="Racine stockage local médiathèque (défaut : <repo>/media/).",
    )
    legal_documents_root: str | None = Field(
        default=None,
        alias="LEGAL_DOCUMENTS_ROOT",
        description="Racine PDFs devis/factures/CGV (défaut : <repo>/documents/).",
    )

    mat_legal_name: str = Field(
        default="Mathias Gibiard",
        alias="MAT_LEGAL_NAME",
    )
    mat_legal_activity: str = Field(
        default="CapCore — CyberForge / Cap Copy",
        alias="MAT_LEGAL_ACTIVITY",
    )
    mat_legal_status: str = Field(
        default="Micro-entrepreneur",
        alias="MAT_LEGAL_STATUS",
    )
    mat_legal_email: str = Field(
        default="capcore.pro@gmail.com",
        alias="MAT_LEGAL_EMAIL",
    )
    mat_siret: str | None = Field(
        default=None,
        alias="MAT_SIRET",
        description="SIRET micro-entrepreneur (affiché sur devis/factures).",
    )
    mat_legal_brand: str = Field(
        default="CapCore",
        alias="MAT_LEGAL_BRAND",
    )

    capcore_notify_email: str = Field(
        default="capcore.pro@gmail.com",
        alias="CAPCORE_NOTIFY_EMAIL",
    )
    brevo_api_key: SecretStr | None = Field(default=None, alias="BREVO_API_KEY")
    brevo_sender_email: str = Field(
        default="noreply@capcore.pro",
        alias="BREVO_SENDER_EMAIL",
        description="Expéditeur vérifié dans Brevo.",
    )
    brevo_sender_name: str = Field(default="CapCore", alias="BREVO_SENDER_NAME")

    telegram_bot_token: SecretStr | None = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str | None = Field(default=None, alias="TELEGRAM_CHAT_ID")

    stripe_secret_key: SecretStr | None = Field(
        default=None,
        alias="STRIPE_SECRET_KEY",
        description="Clé secrète Stripe (Checkout + webhooks).",
    )
    stripe_ecommerce_webhook_secret: SecretStr | None = Field(
        default=None,
        alias="STRIPE_ECOMMERCE_WEBHOOK_SECRET",
        description="Secret de signature webhook Stripe pour ecommerce (optionnel en dev).",
    )
    stripe_desktop_webhook_secret: SecretStr | None = Field(
        default=None,
        alias="STRIPE_DESKTOP_WEBHOOK_SECRET",
        description="Secret de signature webhook Stripe pour mini-apps desktop.",
    )
    stripe_webhook_secret: SecretStr | None = Field(
        default=None,
        alias="STRIPE_WEBHOOK_SECRET",
        description="Secret webhook Stripe global (stripe_service).",
    )
    capcore_site_url: str = Field(
        default="https://capcore.pro",
        alias="CAPCORE_SITE_URL",
        description="URL publique du site capcore.pro (Checkout success/cancel).",
    )

    unsplash_access_key: SecretStr | None = Field(
        default=None,
        alias="UNSPLASH_ACCESS_KEY",
        description="Clé API Unsplash (recherche photos vitrine Next.js).",
    )
    unsplash_http_timeout_seconds: float = Field(
        default=12.0,
        alias="UNSPLASH_HTTP_TIMEOUT_SECONDS",
    )

    pexels_api_key: SecretStr | None = Field(
        default=None,
        alias="PEXELS_API_KEY",
        description="Clé API Pexels (boîte à outils photos).",
    )
    toolbox_http_timeout_seconds: float = Field(
        default=12.0,
        alias="TOOLBOX_HTTP_TIMEOUT_SECONDS",
        description="Timeout HTTP des appels toolbox (Pexels, Iconify, unDraw).",
    )

    firecrawl_api_key: SecretStr | None = Field(
        default=None,
        alias="FIRECRAWL_API_KEY",
        description="Clé API Firecrawl (scrape concurrent / inspiration).",
    )
    firecrawl_http_timeout_seconds: float = Field(
        default=90.0,
        alias="FIRECRAWL_HTTP_TIMEOUT_SECONDS",
    )

    tavily_api_key: SecretStr | None = Field(
        default=None,
        alias="TAVILY_API_KEY",
        description="Clé API Tavily (Extract) pour analyse URL concurrente.",
    )
    tavily_http_timeout_seconds: float = Field(
        default=25.0,
        alias="TAVILY_HTTP_TIMEOUT_SECONDS",
    )

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
    def unsplash_configured(self) -> bool:
        """True si l'API Unsplash est disponible pour les vitrines Next.js."""
        return bool(plain_secret_str(self.unsplash_access_key))

    @property
    def pexels_configured(self) -> bool:
        """True si l'API Pexels est disponible pour la toolbox photos."""
        return bool(plain_secret_str(self.pexels_api_key))

    @property
    def firecrawl_configured(self) -> bool:
        """True si Firecrawl est configuré."""
        return bool(plain_secret_str(self.firecrawl_api_key))

    @property
    def cloudflare_configured(self) -> bool:
        """True si Account ID et token API sont définis dans backend/.env."""
        return bool(
            plain_secret_str(self.cloudflare_account_id)
            and plain_secret_str(self.cloudflare_api_token)
        )

    @property
    def legal_documents_dir(self) -> Path:
        """Répertoire de sortie des PDFs juridiques."""
        explicit = self.legal_documents_root
        if explicit and str(explicit).strip():
            return Path(str(explicit).strip())
        return _ROOT / "documents"

    @property
    def cloudflare_r2_configured(self) -> bool:
        """True si les credentials R2 médiathèque sont définis."""
        return bool(
            plain_secret_str(self.cloudflare_r2_account_id)
            and plain_secret_str(self.cloudflare_r2_access_key_id)
            and plain_secret_str(self.cloudflare_r2_secret_access_key)
            and (self.cloudflare_r2_bucket or "").strip()
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

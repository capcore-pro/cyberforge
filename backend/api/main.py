"""
Factory FastAPI — assemble routes, CORS et métadonnées de l'API.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import API_ROUTERS
from api.routes import meta
from config import refresh_settings
from db.supabase_store import reset_supabase_store

APP_VERSION = "0.1.0"
logger = logging.getLogger(__name__)

REQUIRED_ROUTES = ("/api/health", "/api/projects")


def _collect_route_paths(application: FastAPI) -> set[str]:
    paths: set[str] = set()
    for route in application.routes:
        path = getattr(route, "path", None)
        if path:
            paths.add(path)
    return paths


def _log_registered_routes(application: FastAPI) -> None:
    paths = sorted(_collect_route_paths(application))
    api_paths = [p for p in paths if p.startswith("/api")]
    logger.info("Routes API enregistrées (%s) : %s", len(api_paths), ", ".join(api_paths))
    for required in REQUIRED_ROUTES:
        if required not in paths:
            logger.error("Route manquante : %s", required)
        else:
            logger.info("Route OK : %s", required)


@asynccontextmanager
async def _lifespan(application: FastAPI):
    from config import get_settings, plain_secret_str
    from security.cloudflare_env import load_cloudflare_from_env

    load_cloudflare_from_env()
    settings = get_settings()
    brevo_key = bool(plain_secret_str(settings.brevo_api_key))
    logger.info(
        "Brevo notifications | configured=%s | sender=%s <%s> | dest=%s",
        brevo_key,
        settings.brevo_sender_name,
        settings.brevo_sender_email,
        settings.capcore_notify_email,
    )
    _log_registered_routes(application)
    yield


def create_app() -> FastAPI:
    """Crée et configure l'instance FastAPI."""
    settings = refresh_settings()
    reset_supabase_store()

    application = FastAPI(
        title=settings.app_name,
        version=APP_VERSION,
        description="API backend CyberForge — agents IA et outils de sécurité",
        docs_url="/docs" if settings.app_debug else None,
        redoc_url="/redoc" if settings.app_debug else None,
        lifespan=_lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for api_router, prefix in API_ROUTERS:
        application.include_router(api_router, prefix=prefix)

    application.include_router(meta.router, prefix="/api")

    missing = [r for r in REQUIRED_ROUTES if r not in _collect_route_paths(application)]
    if missing:
        raise RuntimeError(
            f"Routes API manquantes après enregistrement : {missing}. "
            "Vérifiez api/routes/__init__.py et api/main.py."
        )

    return application

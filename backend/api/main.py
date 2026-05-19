"""
Factory FastAPI — assemble routes, CORS et métadonnées de l'API.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import coremind, health, projects
from config import refresh_settings
from db.supabase_store import reset_supabase_store

APP_VERSION = "0.1.0"


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
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health.router, prefix="/api")
    application.include_router(coremind.router, prefix="/api")
    application.include_router(projects.router, prefix="/api")

    return application

"""Routes HTTP — enregistrement centralisé pour éviter les oublis."""

from fastapi import APIRouter

from api.routes import coremind, health, projects

# (router, prefix OpenAPI)
API_ROUTERS: list[tuple[APIRouter, str]] = [
    (health.router, "/api"),
    (coremind.router, "/api"),
    (projects.router, "/api"),
]

__all__ = ["API_ROUTERS", "coremind", "health", "projects"]

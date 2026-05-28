"""Routes HTTP — enregistrement centralisé pour éviter les oublis."""

from fastapi import APIRouter

from api.routes import (
    agents_status,
    clients,
    coremind,
    demos,
    health,
    managed_vitrines,
    notifications,
    pipeline_stream,
    projects,
    public_demos,
    secrets,
    vitrine,
    vitrine_auth,
)

# (router, prefix OpenAPI)
API_ROUTERS: list[tuple[APIRouter, str]] = [
    (health.router, "/api"),
    (agents_status.router, "/api"),
    (coremind.router, "/api"),
    (pipeline_stream.router, "/api"),
    (projects.router, "/api"),
    (managed_vitrines.router, "/api"),
    (clients.router, "/api"),
    (secrets.router, "/api"),
    (demos.router, "/api"),
    (notifications.router, "/api"),
    (vitrine.router, "/api"),
    (vitrine_auth.router, "/api"),
    (public_demos.router, "/api/public"),
]

__all__ = [
    "API_ROUTERS",
    "agents_status",
    "clients",
    "coremind",
    "demos",
    "health",
    "managed_vitrines",
    "notifications",
    "projects",
    "public_demos",
    "secrets",
    "vitrine",
    "vitrine_auth",
]

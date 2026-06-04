"""Routes HTTP — API CyberForge (generate, projects, managed-projects, health)."""

from fastapi import APIRouter

from api.routes import (
    agents_status,
    demos,
    generate,
    health,
    managed_application_web,
    managed_ecommerce,
    managed_extensions,
    managed_site_reservation,
    managed_vitrines,
    notifications,
    projects,
)

API_ROUTERS: list[tuple[APIRouter, str]] = [
    (health.router, "/api"),
    (agents_status.router, "/api"),
    (generate.router, "/api"),
    (projects.router, "/api"),
    (notifications.router, "/api"),
    (demos.router, "/api"),
    (managed_vitrines.router, "/api"),
    (managed_application_web.router, "/api"),
    (managed_ecommerce.router, "/api"),
    (managed_site_reservation.router, "/api"),
    (managed_extensions.router, "/api"),
]

__all__ = [
    "API_ROUTERS",
    "agents_status",
    "demos",
    "generate",
    "health",
    "managed_application_web",
    "managed_ecommerce",
    "managed_extensions",
    "managed_site_reservation",
    "managed_vitrines",
    "notifications",
    "projects",
]

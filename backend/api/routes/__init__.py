"""Routes HTTP — API CyberForge v2 (generate, projects, health, agents)."""

from fastapi import APIRouter

from api.routes import agents_status, generate, health, projects

API_ROUTERS: list[tuple[APIRouter, str]] = [
    (health.router, "/api"),
    (agents_status.router, "/api"),
    (generate.router, "/api"),
    (projects.router, "/api"),
]

__all__ = [
    "API_ROUTERS",
    "agents_status",
    "generate",
    "health",
    "projects",
]

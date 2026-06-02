"""
Point d'entrée uvicorn — lance l'application FastAPI CyberForge.

Usage :
    uvicorn main:app --reload --host 127.0.0.1 --port 8002
"""

from __future__ import annotations

import logging
import time

from pydantic import BaseModel

logger = logging.getLogger(__name__)
_startup_t0 = time.perf_counter()


def _startup_mark(label: str) -> None:
    elapsed_ms = (time.perf_counter() - _startup_t0) * 1000
    logger.info("[startup] %s (+%.0f ms)", label, elapsed_ms)


_startup_mark("begin")

from api.main import create_app

_startup_mark("import api.main")

from cockpit_db import init_db

_startup_mark("import cockpit_db")

from cockpit_router import router as cockpit_router

_startup_mark("import cockpit_router")

from legal_router import router as legal_router

_startup_mark("import legal_router")

from media_router import router as media_router

_startup_mark("import media_router")

from desktop_app_router import router as desktop_app_router

_startup_mark("import desktop_app_router")

from newsletter_router import router as newsletter_router

_startup_mark("import newsletter_router")

from personal_projects_router import router as personal_projects_router

_startup_mark("import personal_projects_router")

from stripe_router import router as stripe_router

_startup_mark("import stripe_router")

from routers.notifications import router as system_notifications_router

_startup_mark("import routers.notifications")

from routers.toolbox import router as toolbox_router

_startup_mark("import routers.toolbox")

from routers.firecrawl import router as firecrawl_router

_startup_mark("import routers.firecrawl")

from routers.cms import panel_router as cms_panel_router
from routers.cms import router as cms_router

_startup_mark("import routers.cms")

_t_init_db = time.perf_counter()
init_db()
logger.info("[startup] init_db done (%.0f ms)", (time.perf_counter() - _t_init_db) * 1000)

_t_create = time.perf_counter()
app = create_app()
logger.info("[startup] create_app done (%.0f ms)", (time.perf_counter() - _t_create) * 1000)

_t_routers = time.perf_counter()


class DatabaseSchemaRequest(BaseModel):
    project_description: str
    project_type: str
    design_system: dict = {}


@app.post("/api/database-schema")
async def generate_database_schema(body: DatabaseSchemaRequest) -> dict:
    from agents import database_ai

    return await database_ai.run(
        project_description=body.project_description,
        project_type=body.project_type,
        design_system=body.design_system or {},
    )


class AuthSchemaRequest(BaseModel):
    project_description: str
    project_type: str
    database_schema: dict = {}


@app.post("/api/auth-schema")
async def generate_auth_schema(body: AuthSchemaRequest) -> dict:
    from agents import auth_ai

    return await auth_ai.run(
        project_description=body.project_description,
        project_type=body.project_type,
        database_schema=body.database_schema or {},
    )


app.include_router(cockpit_router, prefix="/api/cockpit")
app.include_router(media_router, prefix="/api/media")
app.include_router(legal_router, prefix="/api/legal")
app.include_router(newsletter_router, prefix="/api/newsletter")
app.include_router(desktop_app_router, prefix="/api/desktop")
app.include_router(stripe_router, prefix="/api/stripe")
app.include_router(personal_projects_router, prefix="/api/personal-projects")
app.include_router(system_notifications_router, prefix="/api")
app.include_router(toolbox_router, prefix="/api")
app.include_router(firecrawl_router, prefix="/api")
app.include_router(cms_panel_router)
app.include_router(cms_router, prefix="/api")
logger.info("[startup] extra routers mounted (%.0f ms)", (time.perf_counter() - _t_routers) * 1000)

logger.info(
    "[startup] CyberForge backend ready in %.0f ms",
    (time.perf_counter() - _startup_t0) * 1000,
)

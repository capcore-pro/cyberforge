"""
Point d'entrée uvicorn — API CyberForge v2.

Routes principales :
  POST /api/generate
  GET  /api/projects
  GET  /api/projects/{id}
  DELETE /api/projects/{id}
  GET  /api/agents/status
  GET  /api/health
  GET  /api/legal/clients

Usage :
    uvicorn main:app --reload --host 127.0.0.1 --port 8002
"""

from __future__ import annotations

import logging
import time

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

_t_init_db = time.perf_counter()
init_db()
logger.info("[startup] init_db done (%.0f ms)", (time.perf_counter() - _t_init_db) * 1000)

_t_create = time.perf_counter()
app = create_app()

from api.routes.legal import router as legal_router

app.include_router(legal_router, prefix="/api/legal")

_legal_paths = {getattr(r, "path", "") for r in app.routes}
if "/api/legal/clients" not in _legal_paths:
    logger.error(
        "Route manquante après enregistrement legal : /api/legal/clients (paths=%s)",
        sorted(p for p in _legal_paths if p.startswith("/api/legal")),
    )
else:
    logger.info("[startup] Route OK : /api/legal/clients")

logger.info("[startup] create_app done (%.0f ms)", (time.perf_counter() - _t_create) * 1000)

logger.info(
    "[startup] CyberForge backend ready in %.0f ms",
    (time.perf_counter() - _startup_t0) * 1000,
)

"""
Point d'entrée uvicorn — API CyberForge v2.

Routes principales :
  POST /api/generate
  GET  /api/projects
  GET  /api/projects/{id}
  DELETE /api/projects/{id}
  GET  /api/agents/status
  GET  /api/health

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
logger.info("[startup] create_app done (%.0f ms)", (time.perf_counter() - _t_create) * 1000)

logger.info(
    "[startup] CyberForge backend ready in %.0f ms",
    (time.perf_counter() - _startup_t0) * 1000,
)

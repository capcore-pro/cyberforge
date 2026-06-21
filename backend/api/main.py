"""
Factory FastAPI — assemble routes, CORS et métadonnées de l'API.
"""

import logging as _early_log

_early_log.basicConfig(level=_early_log.DEBUG)
_startup = _early_log.getLogger("startup")
_startup.info("[EARLY] api.main loading started")

_startup.info("[EARLY] importing stdlib...")
import logging
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from time import time as _time

_startup.info("[EARLY] stdlib OK")

_startup.info("[EARLY] importing fastapi...")
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

_startup.info("[EARLY] fastapi OK")

_startup.info("[EARLY] importing api.recent_logs...")
from api.recent_logs import attach_ring_buffer_handler

_startup.info("[EARLY] api.recent_logs OK")

_startup.info("[EARLY] importing api.routes...")
from api.routes import API_ROUTERS
from api.routes import meta

_startup.info("[EARLY] api.routes OK — %s routers", len(API_ROUTERS))

_startup.info("[EARLY] importing config...")
from config import refresh_settings

_startup.info("[EARLY] config OK")

_startup.info("[EARLY] importing db stores...")
from db.managed_projects_store import reset_managed_projects_store
from db.supabase_store import reset_supabase_store

_startup.info("[EARLY] db stores OK")

APP_VERSION = "1.0.0"
logger = logging.getLogger(__name__)

REQUIRED_ROUTES = ("/api/health", "/api/projects", "/api/generate", "/api/agents/status")

# Store en RAM — reset au redémarrage
_rate_limit_store: dict = defaultdict(list)

RATE_LIMITS = {
    "/api/generate": (10, 60),
    "/api/secrets/save": (5, 60),
    "/api/knowledge/ingest": (20, 60),
    "/api/pipeline/prospects": (30, 60),
}


def _collect_route_paths(application: FastAPI) -> set[str]:
    paths: set[str] = set()

    def _walk(routes) -> None:
        for route in routes:
            path = getattr(route, "path", None)
            if path:
                paths.add(path)
            sub_routes = getattr(route, "routes", None)
            if sub_routes:
                _walk(sub_routes)

    _walk(application.routes)
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
    attach_ring_buffer_handler()
    settings = refresh_settings()
    reset_supabase_store()
    reset_managed_projects_store()

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

    @application.middleware("http")
    async def latency_middleware(request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - start) * 1000)
        response.headers["X-Response-Time"] = f"{duration_ms}ms"
        if duration_ms > 2000:
            logger.warning(
                "Slow request: %s %s — %sms",
                request.method,
                request.url.path,
                duration_ms,
            )
        return response

    @application.middleware("http")
    async def rate_limit_middleware(request, call_next):
        path = request.url.path
        method = request.method

        if method not in ("POST", "PATCH"):
            return await call_next(request)

        limit_config = None
        for route_prefix, config in RATE_LIMITS.items():
            if path.startswith(route_prefix):
                limit_config = config
                break

        if not limit_config:
            return await call_next(request)

        max_requests, window_seconds = limit_config
        client_key = f"{path}:{request.client.host}"
        now = _time()

        _rate_limit_store[client_key] = [
            t for t in _rate_limit_store[client_key]
            if now - t < window_seconds
        ]

        if len(_rate_limit_store[client_key]) >= max_requests:
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit dépassé",
                    "retry_after": window_seconds,
                },
                headers={"Retry-After": str(window_seconds)},
            )

        _rate_limit_store[client_key].append(now)
        return await call_next(request)

    for api_router, prefix in API_ROUTERS:
        route_count = len(api_router.routes) if hasattr(api_router, "routes") else "N/A"
        logger.info(
            "[ROUTER] type=%s routes=%s prefix=%s",
            type(api_router),
            route_count,
            prefix,
        )
        application.include_router(api_router, prefix=prefix)

    # Module Toolbox UI retiré — pas de routes /api/toolbox.
    application.include_router(meta.router, prefix="/api")

    logger.info(
        "[STARTUP] application.routes types: %s",
        [type(r).__name__ for r in application.routes[:10]],
    )

    missing = [r for r in REQUIRED_ROUTES if r not in _collect_route_paths(application)]
    registered_paths = sorted(_collect_route_paths(application))
    logger.info("[STARTUP] API_ROUTERS count: %s", len(API_ROUTERS))
    logger.info("[STARTUP] Registered routes count: %s", len(registered_paths))
    logger.info("[STARTUP] Registered paths: %s", registered_paths)
    if missing:
        logger.error(
            "[STARTUP] Routes manquantes: %s — registered: %s routes",
            missing,
            len(registered_paths),
        )
        # NE PAS RAISE — laisser démarrer pour diagnostiquer

    return application

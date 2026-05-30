"""
Point d'entrée uvicorn — lance l'application FastAPI CyberForge.

Usage :
    uvicorn main:app --reload --host 127.0.0.1 --port 8002
"""

from api.main import create_app
from cockpit_db import init_db
from cockpit_router import router as cockpit_router
from legal_router import router as legal_router
from media_router import router as media_router
from desktop_app_router import router as desktop_app_router
from newsletter_router import router as newsletter_router
from stripe_router import router as stripe_router
from routers.notifications import router as system_notifications_router
from routers.toolbox import router as toolbox_router
from routers.firecrawl import router as firecrawl_router

init_db()
app = create_app()
app.include_router(cockpit_router, prefix="/api/cockpit")
app.include_router(media_router, prefix="/api/media")
app.include_router(legal_router, prefix="/api/legal")
app.include_router(newsletter_router, prefix="/api/newsletter")
app.include_router(desktop_app_router, prefix="/api/desktop")
app.include_router(stripe_router, prefix="/api/stripe")
app.include_router(system_notifications_router, prefix="/api")
app.include_router(toolbox_router, prefix="/api")
app.include_router(firecrawl_router, prefix="/api")

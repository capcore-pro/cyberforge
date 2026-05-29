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

init_db()
app = create_app()
app.include_router(cockpit_router, prefix="/api/cockpit")
app.include_router(media_router, prefix="/api/media")
app.include_router(legal_router, prefix="/api/legal")

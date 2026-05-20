"""
Point d'entrée uvicorn — lance l'application FastAPI CyberForge.

Usage :
    uvicorn main:app --reload --host 127.0.0.1 --port 8002
"""

from api.main import create_app

app = create_app()

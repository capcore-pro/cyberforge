# Réexport — cohérent avec l'architecture CyberForge
try:
    from ..api.routes.content import router
except ImportError:
    from api.routes.content import router

__all__ = ["router"]

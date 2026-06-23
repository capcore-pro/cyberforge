# Réexport — cohérent avec l'architecture CyberForge
try:
    from ..api.routes.idea import router
except ImportError:
    from api.routes.idea import router

__all__ = ["router"]

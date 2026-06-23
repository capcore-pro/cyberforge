try:
    from ..api.routes.portal import router
except ImportError:
    from api.routes.portal import router

__all__ = ["router"]

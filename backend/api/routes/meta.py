"""
Routes meta — diagnostic de l'API (routes enregistrées).
"""

from fastapi import APIRouter, Request

router = APIRouter(tags=["meta"])


@router.get("/routes")
async def list_registered_routes(request: Request) -> dict[str, object]:
    """Liste les routes FastAPI enregistrées (debug)."""
    paths: list[str] = []
    for route in request.app.routes:
        path = getattr(route, "path", None)
        if not path:
            continue
        methods = sorted(getattr(route, "methods", None) or [])
        if methods:
            paths.append(f"{','.join(methods)} {path}")
        else:
            paths.append(str(path))

    paths.sort()
    return {
        "app": "CyberForge API",
        "projects_route_registered": any("/api/projects" in p for p in paths),
        "routes": paths,
    }

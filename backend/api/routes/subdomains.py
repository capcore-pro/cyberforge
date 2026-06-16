"""
Routes API — sous-domaines automatiques capcore.pro.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db.supabase_store import SupabaseStoreError, get_supabase_store
from tools.subdomain_service import SubdomainError, subdomain_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["subdomains"])


class CreateSubdomainBody(BaseModel):
    client_name: str = Field(..., min_length=1, max_length=200)
    project_id: str | None = Field(default=None, max_length=128)


@router.post("/subdomains/create")
async def create_subdomain(body: CreateSubdomainBody) -> dict:
    """Crée un CNAME nom-client.capcore.pro et met à jour projects.demo_url."""
    try:
        result = await subdomain_service.create_subdomain(
            body.client_name,
            project_id=body.project_id,
        )
    except SubdomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    project_id = (body.project_id or "").strip()
    if project_id:
        store = get_supabase_store()
        if store.is_configured():
            try:
                await store.update_project_demo_url(project_id, result["url"])
            except SupabaseStoreError as exc:
                logger.warning(
                    "Sous-domaine créé mais demo_url non mise à jour | project=%s | %s",
                    project_id,
                    exc,
                )
                result["project_update_warning"] = str(exc)

    return result


@router.delete("/subdomains/{client_name}")
async def delete_subdomain(client_name: str) -> dict:
    """Supprime le sous-domaine DNS pour un nom client."""
    try:
        deleted = await subdomain_service.delete_subdomain(client_name)
    except SubdomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"deleted": deleted, "client_name": client_name}


@router.get("/subdomains")
async def list_subdomains() -> dict:
    """Liste les sous-domaines CNAME capcore.pro."""
    try:
        items = await subdomain_service.list_subdomains()
    except SubdomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"items": items, "count": len(items)}

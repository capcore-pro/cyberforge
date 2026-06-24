"""
Portal Router — CyberForge
Endpoints pour le portail client client.capcore.pro
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.portal_agent import portal_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portal", tags=["portal"])


class CreateClientRequest(BaseModel):
    email: str
    full_name: str
    company: str = ""
    plan: str = "starter"
    password: str | None = None


class AddSiteRequest(BaseModel):
    client_id: str
    site_name: str
    html_content: str
    site_url: str = ""
    cloudflare_project_name: str = ""
    sector: str = ""
    project_type: str = "vitrine_next"
    project_id: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class EditItem(BaseModel):
    type: str = "text"
    selector: str
    old_value: str = ""
    new_value: str = ""


class SaveDeployRequest(BaseModel):
    site_id: str
    client_id: str
    edits: list[EditItem] = Field(default_factory=list)
    html_updated: str


class ToggleClientRequest(BaseModel):
    client_id: str
    is_active: bool


@router.post("/clients")
async def create_portal_client(request: CreateClientRequest) -> dict:
    """Crée un client portail — appelé par Mat depuis CyberForge."""
    try:
        client = await portal_agent.create_client(
            email=request.email,
            full_name=request.full_name,
            company=request.company,
            plan=request.plan,
            password=request.password,
        )
        return {"success": True, "client": client}
    except Exception as e:
        logger.exception("Portal create client error")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/clients")
async def list_portal_clients() -> dict:
    """Liste tous les clients portail."""
    try:
        clients = await portal_agent.list_clients()
        return {"clients": clients}
    except Exception as e:
        logger.exception("Portal list clients error")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/clients/toggle")
async def toggle_portal_client(request: ToggleClientRequest) -> dict:
    """Active/désactive un client."""
    try:
        await portal_agent.toggle_client(request.client_id, request.is_active)
        return {"success": True}
    except Exception as e:
        logger.exception("Portal toggle client error")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/sites")
async def add_portal_site(request: AddSiteRequest) -> dict:
    """Ajoute un site au portail d'un client."""
    try:
        site = await portal_agent.add_site(
            client_id=request.client_id,
            site_name=request.site_name,
            html_content=request.html_content,
            site_url=request.site_url,
            cloudflare_project_name=request.cloudflare_project_name,
            sector=request.sector,
            project_type=request.project_type,
            project_id=request.project_id,
        )
        return {"success": True, "site": site}
    except Exception as e:
        logger.exception("Portal add site error")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/auth/login")
async def portal_login(request: LoginRequest) -> dict:
    """Authentifie un client portail."""
    try:
        client = await portal_agent.verify_client(request.email, request.password)
        if not client:
            raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

        sites = await portal_agent.get_client_sites(str(client["id"]))
        return {
            "success": True,
            "client": {
                "id": client["id"],
                "email": client["email"],
                "full_name": client["full_name"],
                "company": client["company"],
                "plan": client["plan"],
                "subscription_status": client.get("subscription_status") or "trial",
                "trial_ends_at": client.get("trial_ends_at"),
                "subscription_ends_at": client.get("subscription_ends_at"),
                "billing_interval": client.get("billing_interval") or "monthly",
                "onboarding_done": client.get("onboarding_done", False),
                "site_url": client.get("site_url")
                or (sites[0].get("site_url") if sites else None),
            },
            "sites": sites,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Portal login error")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/sites/{client_id}")
async def get_client_sites(client_id: str) -> dict:
    """Retourne les sites d'un client."""
    try:
        sites = await portal_agent.get_client_sites(client_id)
        return {"sites": sites}
    except Exception as e:
        logger.exception("Portal get sites error")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/save-deploy")
async def save_and_deploy(request: SaveDeployRequest) -> dict:
    """Sauvegarde les modifications et redéploie."""
    try:
        return await portal_agent.save_and_deploy(
            site_id=request.site_id,
            client_id=request.client_id,
            edits=[e.model_dump() for e in request.edits],
            html_updated=request.html_updated,
        )
    except Exception as e:
        logger.exception("Portal save-deploy error")
        raise HTTPException(status_code=500, detail=str(e)) from e

"""
Portal Router — CyberForge
Endpoints pour le portail client client.capcore.pro
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.portal_agent import portal_agent
from utils.supabase_client import get_supabase

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


@router.get("/stats")
async def get_portal_stats():
    """Statistiques globales portail — clients abonnés + MRR + revenus one-shot."""
    try:
        supabase = get_supabase()
        now = datetime.now(timezone.utc)
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # --- Clients portail ---
        clients_res = (
            supabase.table("portal_clients")
            .select("id, subscription_status, trial_ends_at")
            .execute()
        )
        clients = clients_res.data or []

        clients_actifs = len([c for c in clients if c.get("subscription_status") == "active"])
        clients_trial = len([c for c in clients if c.get("subscription_status") == "trial"])
        clients_expires = len(
            [c for c in clients if c.get("subscription_status") in ("expired", "canceled")]
        )

        # --- MRR abonnements Stripe (portal_subscriptions) ---
        subs_res = (
            supabase.table("portal_subscriptions")
            .select("amount_eur, status")
            .eq("status", "active")
            .execute()
        )
        subs = subs_res.data or []
        mrr_abonnements = round(sum(float(s.get("amount_eur") or 0) for s in subs), 2)

        # --- MRR gestion déléguée (portal_management_plans) ---
        plans_res = (
            supabase.table("portal_management_plans")
            .select("price_eur, status")
            .eq("status", "active")
            .execute()
        )
        plans = plans_res.data or []
        mrr_gestion = round(sum(float(p.get("price_eur") or 0) for p in plans), 2)

        # --- MRR total + ARR ---
        mrr_total = round(mrr_abonnements + mrr_gestion, 2)
        arr_total = round(mrr_total * 12, 2)

        # --- Revenus one-shot projets ---
        projects_res = (
            supabase.table("projects")
            .select("price_eur, price_paid_at")
            .not_.is_("price_eur", "null")
            .gt("price_eur", 0)
            .execute()
        )
        projects = projects_res.data or []

        revenus_oneshot_total = round(
            sum(float(p.get("price_eur") or 0) for p in projects), 2
        )
        revenus_oneshot_mois = round(
            sum(
                float(p.get("price_eur") or 0)
                for p in projects
                if p.get("price_paid_at")
                and p["price_paid_at"] >= current_month_start.isoformat()
            ),
            2,
        )

        return {
            "success": True,
            "clients_actifs": clients_actifs,
            "clients_trial": clients_trial,
            "clients_expires": clients_expires,
            "clients_total": len(clients),
            "mrr_abonnements": mrr_abonnements,
            "mrr_gestion_deleguee": mrr_gestion,
            "mrr_total": mrr_total,
            "arr_total": arr_total,
            "revenus_oneshot_mois": revenus_oneshot_mois,
            "revenus_oneshot_total": revenus_oneshot_total,
        }

    except Exception as e:
        logger.exception("Portal stats error")
        return {"success": False, "error": str(e)}


@router.get("/management-plans")
async def get_management_plans():
    """Liste tous les plans de gestion déléguée actifs."""
    try:
        supabase = get_supabase()
        res = (
            supabase.table("portal_management_plans")
            .select("*, portal_clients(full_name, email)")
            .eq("status", "active")
            .execute()
        )
        return {"success": True, "plans": res.data or []}
    except Exception as e:
        logger.exception("Portal management-plans error")
        return {"success": False, "plans": [], "error": str(e)}

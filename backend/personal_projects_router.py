"""
API projets personnels Mat — usage, commercialisation, mini-apps P13.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config import get_settings
import personal_projects_db as db

router = APIRouter(tags=["personal-projects"])

PersonalUsage = Literal["personal", "one_shot", "subscription"]

_DESKTOP_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "facture_express",
        "title": "Facture Express",
        "description": "Mini-app desktop — devis et factures PDF en un clic, idéal pour indépendants.",
        "icon": "🧾",
        "preview_features": ["Devis / factures", "Export PDF", "Lignes dynamiques"],
    },
    {
        "id": "lead_tracker",
        "title": "Lead Tracker",
        "description": "CRM léger pour suivre prospects, statuts et relances commerciales.",
        "icon": "📊",
        "preview_features": ["Pipeline leads", "Statuts", "Stockage local"],
    },
    {
        "id": "caisse",
        "title": "Caisse CapCore",
        "description": "Point de vente simplifié — articles, panier et encaissement.",
        "icon": "🛒",
        "preview_features": ["Catalogue", "Panier", "Ticket"],
    },
]


class PersonalProjectCreate(BaseModel):
    title: str = Field(min_length=1)
    usage_type: PersonalUsage = "personal"
    price_eur: float | None = Field(default=None, ge=0)
    commercial_description: str | None = None
    project_key: str | None = None
    supabase_project_id: str | None = None
    managed_id: str | None = None
    demo_id: str | None = None
    app_type: str | None = None


class PersonalProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    usage_type: PersonalUsage | None = None
    price_eur: float | None = Field(default=None, ge=0)
    commercial_description: str | None = None
    project_key: str | None = None
    supabase_project_id: str | None = None
    managed_id: str | None = None
    demo_id: str | None = None
    sale_link: str | None = None
    sales_count: int | None = Field(default=None, ge=0)
    revenue_eur: float | None = Field(default=None, ge=0)


class ConvertToClientBody(BaseModel):
    client_id: str = Field(min_length=1)


class PublishTemplateBody(BaseModel):
    price_eur: float = Field(gt=0)
    commercial_description: str = Field(min_length=1)


def _capcore_base() -> str:
    settings = get_settings()
    return (getattr(settings, "capcore_site_url", None) or "https://capcore.pro").rstrip("/")


def _sale_link_for(usage: str, app_type: str | None, price: float | None) -> str | None:
    base = _capcore_base()
    if usage == "one_shot" and app_type:
        return f"{base}/apps/{app_type.replace('_', '-')}"
    if usage in ("one_shot", "subscription") and price:
        return f"{base}/apps/checkout"
    return None


@router.get("/templates")
async def list_desktop_templates() -> list[dict[str, Any]]:
    return _DESKTOP_TEMPLATES


@router.get("")
async def list_personal_projects() -> list[dict[str, Any]]:
    return db.list_personal_projects()


@router.post("", status_code=201)
async def create_personal_project(body: PersonalProjectCreate) -> dict[str, Any]:
    try:
        row = db.create_personal_project(
            title=body.title,
            usage_type=body.usage_type,
            price_eur=body.price_eur,
            commercial_description=body.commercial_description,
            project_key=body.project_key,
            supabase_project_id=body.supabase_project_id,
            managed_id=body.managed_id,
            demo_id=body.demo_id,
            app_type=body.app_type,
            sale_link=_sale_link_for(body.usage_type, body.app_type, body.price_eur),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return row


@router.get("/{project_id}")
async def get_personal_project(project_id: str) -> dict[str, Any]:
    row = db.get_personal_project(project_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Projet perso introuvable.")
    return row


@router.patch("/{project_id}")
async def update_personal_project(
    project_id: str,
    body: PersonalProjectUpdate,
) -> dict[str, Any]:
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        row = db.get_personal_project(project_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Projet perso introuvable.")
        return row
    try:
        row = db.update_personal_project(project_id, **fields)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="Projet perso introuvable.")
    return row


@router.delete("/{project_id}", status_code=204)
async def delete_personal_project(project_id: str) -> None:
    if not db.delete_personal_project(project_id):
        raise HTTPException(status_code=404, detail="Projet perso introuvable.")


@router.post("/{project_id}/convert-to-client")
async def convert_to_client(
    project_id: str,
    body: ConvertToClientBody,
) -> dict[str, Any]:
    row = db.get_personal_project(project_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Projet perso introuvable.")

    demo_id = row.get("demo_id")
    if demo_id:
        try:
            from db.demos_store import get_demos_store

            store = get_demos_store()
            await store.update_client_id(str(demo_id), body.client_id.strip())
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Association client impossible : {exc}",
            ) from exc

    db.delete_personal_project(project_id)
    return {
        "converted": True,
        "client_id": body.client_id.strip(),
        "demo_id": demo_id,
    }


@router.post("/templates/{app_type}/publish")
async def publish_template(app_type: str, body: PublishTemplateBody) -> dict[str, Any]:
    app_id = app_type.strip().lower()
    template = next((t for t in _DESKTOP_TEMPLATES if t["id"] == app_id), None)
    if template is None:
        raise HTTPException(status_code=404, detail="Template inconnu.")

    base = _capcore_base()
    slug = app_id.replace("_", "-")
    sale_url = f"{base}/apps/{slug}"

    row = db.create_personal_project(
        title=str(template["title"]),
        usage_type="one_shot",
        price_eur=body.price_eur,
        commercial_description=body.commercial_description.strip(),
        app_type=app_id,
        sale_link=sale_url,
    )
    updated = db.update_personal_project(
        str(row["id"]),
        published_on_capcore=True,
    )
    return {
        "project": updated or row,
        "publish_url": sale_url,
        "message": f"Package préparé pour {sale_url}",
    }

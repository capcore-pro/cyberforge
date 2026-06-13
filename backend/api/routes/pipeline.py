"""
Routes API — Pipeline Commercial (prospects Kanban).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from db.prospect_store import STATUTS, get_prospect_store
from db.supabase_store import SupabaseStoreError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["pipeline"])


class CreateProspectRequest(BaseModel):
    nom: str = Field(..., min_length=1, max_length=255)
    entreprise: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    telephone: str | None = Field(default=None, max_length=50)
    secteur: str | None = Field(default=None, max_length=100)
    source: str = Field(default="manuel", max_length=100)
    valeur_estimee: float = Field(default=0, ge=0)
    notes: str | None = Field(default=None, max_length=5000)


class UpdateProspectRequest(BaseModel):
    nom: str | None = Field(default=None, max_length=255)
    entreprise: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    telephone: str | None = Field(default=None, max_length=50)
    secteur: str | None = Field(default=None, max_length=100)
    source: str | None = Field(default=None, max_length=100)
    valeur_estimee: float | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=5000)
    demo_url: str | None = Field(default=None, max_length=2000)


class MoveStatutRequest(BaseModel):
    statut: str = Field(..., min_length=1, max_length=50)


class AddInteractionRequest(BaseModel):
    type: str = Field(..., min_length=1, max_length=50)
    notes: str | None = Field(default=None, max_length=5000)


@router.get("/pipeline/prospects")
async def list_prospects(statut: str | None = None) -> list[dict]:
    store = get_prospect_store()
    if not store.is_configured():
        return []
    try:
        return await store.list_all(statut=statut)
    except SupabaseStoreError as exc:
        logger.warning("list_prospects: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/pipeline/prospects")
async def create_prospect(body: CreateProspectRequest) -> dict:
    store = get_prospect_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        return await store.create(
            nom=body.nom,
            entreprise=body.entreprise,
            email=body.email,
            telephone=body.telephone,
            secteur=body.secteur,
            source=body.source,
            valeur_estimee=body.valeur_estimee,
            notes=body.notes,
        )
    except SupabaseStoreError as exc:
        logger.warning("create_prospect: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/pipeline/prospects/{prospect_id}")
async def update_prospect(prospect_id: str, body: UpdateProspectRequest) -> dict:
    store = get_prospect_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    updates = body.model_dump(exclude_none=True)
    if not updates:
        row = await store.get_by_id(prospect_id)
        if not row:
            raise HTTPException(status_code=404, detail="Prospect introuvable.")
        return row
    try:
        return await store.update(prospect_id, updates)
    except SupabaseStoreError as exc:
        logger.warning("update_prospect: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/pipeline/prospects/{prospect_id}/statut")
async def move_prospect_statut(
    prospect_id: str,
    body: MoveStatutRequest,
) -> dict:
    store = get_prospect_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    if body.statut not in STATUTS:
        raise HTTPException(status_code=400, detail="Statut invalide.")
    try:
        return await store.move_statut(prospect_id, body.statut)
    except SupabaseStoreError as exc:
        logger.warning("move_prospect_statut: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/pipeline/prospects/{prospect_id}")
async def delete_prospect(prospect_id: str) -> dict[str, bool]:
    store = get_prospect_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        await store.delete(prospect_id)
        return {"ok": True}
    except SupabaseStoreError as exc:
        logger.warning("delete_prospect: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/pipeline/prospects/{prospect_id}/interactions")
async def list_prospect_interactions(prospect_id: str) -> list[dict]:
    store = get_prospect_store()
    if not store.is_configured():
        return []
    try:
        return await store.get_interactions(prospect_id)
    except SupabaseStoreError as exc:
        logger.warning("list_prospect_interactions: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/pipeline/prospects/{prospect_id}/interactions")
async def add_prospect_interaction(
    prospect_id: str,
    body: AddInteractionRequest,
) -> dict:
    store = get_prospect_store()
    if not store.is_configured():
        raise HTTPException(status_code=503, detail="Supabase non configuré.")
    try:
        return await store.add_interaction(
            prospect_id,
            body.type,
            notes=body.notes,
        )
    except SupabaseStoreError as exc:
        logger.warning("add_prospect_interaction: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/pipeline/stats")
async def pipeline_stats() -> dict:
    store = get_prospect_store()
    if not store.is_configured():
        return {
            "par_statut": {},
            "total_prospects": 0,
            "valeur_pipeline": 0,
            "taux_conversion": 0,
            "prospects_ce_mois": 0,
        }
    try:
        return await store.get_stats()
    except SupabaseStoreError as exc:
        logger.warning("pipeline_stats: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc

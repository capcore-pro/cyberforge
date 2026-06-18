"""
CyberForge — Video Client Router
Routes pour la gestion des commandes vidéo clients.
"""

from __future__ import annotations

import io
import logging
import os
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from supabase import create_client
from typing import Optional

from agents.video_sector_prompts import get_available_sectors, get_prompts_for_brief
from services.video_client_scenes import (
    build_client_scene_objects,
    generate_french_descriptions,
)
from utils.pdf_generator import generate_brief_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/video-client", tags=["video-client"])

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
)


# ─── Schémas ────────────────────────────────────────────────────────────────

class VideoClientOrderCreate(BaseModel):
    client_name: str
    client_email: str
    client_company: Optional[str] = None
    client_phone: Optional[str] = None

    secteur: str
    objectif: str
    ton: str
    produits_services: Optional[str] = None
    public_cible: Optional[str] = None
    slogan: Optional[str] = None
    couleurs_marque: Optional[str] = None
    duree_souhaitee: int = 30
    exemples_references: Optional[str] = None
    notes_libres: Optional[str] = None

    nb_scenes: int = 5
    musique_premium: bool = False
    overlay_texte: bool = True
    livraison_express: bool = False


class PdfBriefRequest(BaseModel):
    client_name: str
    client_email: str
    client_company: Optional[str] = None
    secteur: str


class ClientScenePayload(BaseModel):
    description_fr: str = ""
    prompt_en: str = ""


class LaunchKlingRequest(BaseModel):
    scenes: list[ClientScenePayload] = Field(default_factory=list)


# ─── Helpers ─────────────────────────────────────────────────────────────────

_SCENE_MOODS = ("opening", "build", "tension", "climax", "resolution", "reveal")


def _enrich_prompts_for_order(order: dict) -> list[str]:
    base_prompts = get_prompts_for_brief(
        secteur=order["secteur"],
        ton=order["ton"],
        nb_scenes=order["nb_scenes"],
    )
    enriched: list[str] = []
    for prompt in base_prompts:
        enriched_prompt = prompt
        if order.get("produits_services"):
            enriched_prompt += f", featuring {order['produits_services']}"
        if order.get("couleurs_marque"):
            enriched_prompt += f", brand colors: {order['couleurs_marque']}"
        enriched.append(enriched_prompt)
    return enriched


async def _build_scenes_for_order(order: dict) -> list[dict]:
    prompts_en = _enrich_prompts_for_order(order)
    descriptions_fr = await generate_french_descriptions(
        prompts_en,
        secteur=order.get("secteur", ""),
    )
    return build_client_scene_objects(prompts_en, descriptions_fr)


def _client_scenes_to_builder(client_scenes: list[dict]) -> list[dict]:
    """Convertit description_fr + prompt_en vers le format Video Builder."""
    scenes: list[dict] = []
    for index, scene in enumerate(client_scenes, start=1):
        prompt_en = (scene.get("prompt_en") or scene.get("prompt") or "").strip()
        description_fr = (scene.get("description_fr") or "").strip()
        if not prompt_en:
            continue
        scenes.append(
            {
                "scene_number": index,
                "title": f"Scène {index}",
                "description_fr": description_fr or prompt_en,
                "prompt": prompt_en,
                "camera_move": "slow dolly forward",
                "mood": _SCENE_MOODS[min(index - 1, len(_SCENE_MOODS) - 1)],
                "duration": 5,
            }
        )
    return scenes


def _normalize_client_scenes_payload(raw_scenes: list[ClientScenePayload]) -> list[dict]:
    normalized: list[dict] = []
    for scene in raw_scenes:
        prompt_en = scene.prompt_en.strip()
        if not prompt_en:
            continue
        normalized.append(
            {
                "description_fr": scene.description_fr.strip(),
                "prompt_en": prompt_en,
            }
        )
    return normalized


def _order_brief_text(order: dict) -> str:
    parts = [order.get("objectif", "")]
    if order.get("produits_services"):
        parts.append(order["produits_services"])
    if order.get("public_cible"):
        parts.append(f"Public: {order['public_cible']}")
    if order.get("notes_libres"):
        parts.append(order["notes_libres"])
    return " — ".join(p for p in parts if p).strip(" —")


# ─── Estimateur de prix ──────────────────────────────────────────────────────

def calculate_price(
    nb_scenes: int,
    duree: int,
    musique_premium: bool,
    overlay_texte: bool,
    livraison_express: bool,
) -> dict:
    base = nb_scenes * 100
    if duree > 30:
        base += (duree - 30) * 10
    if musique_premium:
        base += 150
    if overlay_texte:
        base += 50
    if livraison_express:
        base += 200

    return {
        "prix_estime_min": base,
        "prix_estime_max": int(base * 1.6),
    }


# ─── Route 1 — Générer le PDF brief ─────────────────────────────────────────

@router.post("/generate-pdf")
async def generate_pdf_brief(data: PdfBriefRequest):
    """Génère un PDF formulaire brief vidéo à envoyer au client par email."""
    try:
        pdf_bytes = generate_brief_pdf(
            client_name=data.client_name,
            client_email=data.client_email,
            client_company=data.client_company or "",
            secteur=data.secteur,
        )
        filename = f"Brief_Video_{data.client_name.replace(' ', '_')}.pdf"
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ─── Route 2 — Sauvegarder un brief client ───────────────────────────────────

@router.post("/orders")
async def create_order(data: VideoClientOrderCreate):
    """Sauvegarde le brief client reçu et retourne l'estimation de prix."""
    prix = calculate_price(
        nb_scenes=data.nb_scenes,
        duree=data.duree_souhaitee,
        musique_premium=data.musique_premium,
        overlay_texte=data.overlay_texte,
        livraison_express=data.livraison_express,
    )

    order = {
        "id": str(uuid.uuid4()),
        "client_name": data.client_name,
        "client_email": data.client_email,
        "client_company": data.client_company,
        "client_phone": data.client_phone,
        "secteur": data.secteur,
        "objectif": data.objectif,
        "ton": data.ton,
        "produits_services": data.produits_services,
        "public_cible": data.public_cible,
        "slogan": data.slogan,
        "couleurs_marque": data.couleurs_marque,
        "duree_souhaitee": data.duree_souhaitee,
        "exemples_references": data.exemples_references,
        "notes_libres": data.notes_libres,
        "nb_scenes": data.nb_scenes,
        "musique_premium": data.musique_premium,
        "overlay_texte": data.overlay_texte,
        "livraison_express": data.livraison_express,
        "prix_estime_min": prix["prix_estime_min"],
        "prix_estime_max": prix["prix_estime_max"],
        "status": "brief_recu",
    }

    result = supabase.table("video_client_orders").insert(order).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Erreur sauvegarde brief")

    return {
        "order_id": order["id"],
        "prix_estime_min": prix["prix_estime_min"],
        "prix_estime_max": prix["prix_estime_max"],
        "message": "Brief sauvegardé avec succès",
    }


# ─── Route 3 — Lancer la génération depuis un brief ─────────────────────────

@router.post("/orders/{order_id}/generate")
async def generate_from_order(order_id: str):
    """
    Prépare les prompts sectoriels adaptés au brief client.
    Retourne les scènes générées pour validation avant lancement Kling.
    """
    result = (
        supabase.table("video_client_orders")
        .select("*")
        .eq("id", order_id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Commande introuvable")

    order = result.data

    try:
        scene_objects = await _build_scenes_for_order(order)
    except Exception as exc:
        logger.exception("generate_from_order failed for %s", order_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    supabase.table("video_client_orders").update({"status": "en_generation"}).eq(
        "id", order_id
    ).execute()

    return {
        "order_id": order_id,
        "client_name": order["client_name"],
        "secteur": order["secteur"],
        "scenes": scene_objects,
        "nb_scenes": order["nb_scenes"],
        "duree_souhaitee": order["duree_souhaitee"],
        "slogan": order.get("slogan", ""),
        "message": "Scènes générées — tu peux les modifier avant de lancer Kling",
    }


# ─── Route 3b — Créer video_project et lancer le Video Builder ───────────────

@router.post("/orders/{order_id}/launch")
async def launch_kling_from_order(order_id: str, body: LaunchKlingRequest):
    """
    Crée un video_project depuis le brief client
    et retourne l'ID pour redirection vers le Video Builder.
    """
    result = (
        supabase.table("video_client_orders")
        .select("*")
        .eq("id", order_id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Commande introuvable")

    order = result.data
    client_scenes = _normalize_client_scenes_payload(body.scenes)

    if not client_scenes:
        client_scenes = await _build_scenes_for_order(order)

    scenes = _client_scenes_to_builder(client_scenes)
    if not scenes:
        raise HTTPException(status_code=400, detail="Aucune scène à lancer")

    display_name = order.get("client_company") or order["client_name"]
    video_project_id = str(uuid.uuid4())

    project_data = {
        "id": video_project_id,
        "title": display_name,
        "brand": "cyberforge",
        "brief": _order_brief_text(order),
        "ambiance": "cinématique premium",
        "status": "draft",
        "scenes": scenes,
        "scenes_data": client_scenes,
        "secteur": order["secteur"],
        "ton": order["ton"],
        "client_order_id": order_id,
        "source": "client_brief",
    }

    proj_result = supabase.table("video_projects").insert(project_data).execute()

    if not proj_result.data:
        raise HTTPException(status_code=500, detail="Erreur création video_project")

    clips = []
    for scene in scenes:
        clips.append(
            {
                "id": str(uuid.uuid4()),
                "project_id": video_project_id,
                "scene_number": scene["scene_number"],
                "title": scene.get("title", ""),
                "prompt": scene["prompt"],
                "camera_move": scene.get("camera_move", ""),
                "mood": scene.get("mood", ""),
                "status": "pending",
            }
        )
    supabase.table("video_clips").insert(clips).execute()

    supabase.table("video_client_orders").update(
        {
            "status": "en_generation",
            "video_project_id": video_project_id,
        }
    ).eq("id", order_id).execute()

    return {
        "video_project_id": video_project_id,
        "brand": display_name,
        "nb_scenes": len(scenes),
        "message": "Projet créé — redirection Video Builder",
    }


# ─── Route 4 — Liste des commandes ──────────────────────────────────────────

@router.get("/orders")
async def list_orders():
    result = (
        supabase.table("video_client_orders")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


# ─── Route 5 — Secteurs disponibles ─────────────────────────────────────────

@router.get("/sectors")
async def list_sectors():
    return {"sectors": get_available_sectors()}

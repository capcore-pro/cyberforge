"""Routes VisualAI — /api/visual/*"""

from __future__ import annotations

from typing import Literal
import uuid as uuid_lib

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from agents.content_agent import content_agent
from agents.visual_agent import visual_agent
from utils.supabase_client import get_supabase

router = APIRouter(prefix="/api/visual", tags=["visual"])

# Préfixe Storage ; user_id DB = UUID auth.users (service role, desktop mono-opérateur)
POSE_GALLERY_STORAGE_PREFIX = "capcore"
POSE_GALLERY_USER_ID = "00000000-0000-0000-0000-000000000001"


class AvatarPoseRequest(BaseModel):
    pose_key: str
    format_key: Literal["9:16", "1:1", "1:1_facebook", "16:9"] = "1:1"


class SocialVisualRequest(BaseModel):
    texte_principal: str = Field(min_length=1, max_length=80)
    sous_texte: str = Field(default="CapCore Studio Digital", max_length=60)
    format_key: Literal["9:16", "1:1", "1:1_facebook", "16:9"] = "1:1"
    style: Literal["professionnel", "moderne", "minimaliste"] = "professionnel"
    pose_key: str = "presentation"
    sujet_context: str = ""
    image_prompt: str | None = None
    image_prompt_strength: float = 0.85


@router.get("/config")
def get_visual_config():
    return {
        "formats": visual_agent.get_formats(),
        "poses": visual_agent.get_avatar_poses(),
        "styles": [
            {"key": "professionnel", "label": "Professionnel"},
            {"key": "moderne", "label": "Moderne"},
            {"key": "minimaliste", "label": "Minimaliste"},
        ],
    }


@router.post("/avatar-pose")
async def generate_avatar_pose(body: AvatarPoseRequest):
    result = await visual_agent.generate_avatar_pose(
        pose_key=body.pose_key,
        format_key=body.format_key,
    )
    if "error" in result:
        return {"success": False, "error": result["error"]}
    return {"success": True, **result}


@router.post("/social-visual")
async def generate_social_visual(request: SocialVisualRequest):
    result = await visual_agent.generate_social_visual(
        texte_principal=request.texte_principal,
        sous_texte=request.sous_texte,
        format_key=request.format_key,
        style=request.style,
        pose_key=request.pose_key,
        sujet_context=request.sujet_context,
        image_prompt=request.image_prompt,
        image_prompt_strength=request.image_prompt_strength,
    )
    if "error" in result:
        return {"success": False, "error": result["error"]}
    return {"success": True, **result}


@router.post("/upload-reference")
async def upload_reference_image(file: UploadFile = File(...)):
    """Upload une image de référence vers Supabase Storage — retourne l'URL signée."""
    try:
        supabase = get_supabase()

        if file.content_type not in ["image/png", "image/jpeg", "image/webp"]:
            raise HTTPException(
                status_code=400,
                detail="Format non supporté — PNG, JPEG ou WebP uniquement",
            )

        file_bytes = await file.read()
        extension = file.content_type.split("/")[-1]
        storage_path = f"references/{uuid_lib.uuid4().hex}.{extension}"

        supabase.storage.from_("visual-references").upload(
            path=storage_path,
            file=file_bytes,
            file_options={
                "content-type": file.content_type,
                "upsert": "true",
            },
        )

        result = supabase.storage.from_("visual-references").create_signed_url(
            path=storage_path,
            expires_in=86400,
        )
        signed_url = result["signedURL"]

        return {"reference_url": signed_url, "storage_path": storage_path}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CarouselRequest(BaseModel):
    sujet_type: str
    sujet_label: str
    format_reseau: str = "1:1"


class CarouselSlide(BaseModel):
    slide_index: int
    role: str
    image_url: str
    titre: str
    sous_texte: str


class CarouselResponse(BaseModel):
    slides: list[CarouselSlide]
    textes_utilises: list[dict]


@router.post("/carousel", response_model=CarouselResponse)
async def generate_carousel(request: CarouselRequest):
    """Génère un carrousel de 5 visuels FLUX pour CapCore — Mode CapCore uniquement."""
    try:
        textes = await content_agent.generate_carousel_texts(
            sujet_label=request.sujet_label
        )

        slides = await visual_agent.generate_carousel(
            textes=textes,
            format_reseau=request.format_reseau,
        )

        return CarouselResponse(
            slides=[CarouselSlide(**s) for s in slides],
            textes_utilises=textes,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Modèles galerie poses ---

class SavePoseRequest(BaseModel):
    pose_key: str
    image_url: str


class PoseItem(BaseModel):
    id: str
    pose_key: str
    image_url: str  # signed URL 1h
    storage_path: str
    created_at: str


class SavePoseResponse(BaseModel):
    success: bool
    pose_key: str
    storage_path: str


# --- Routes galerie poses ---

@router.get("/poses")
async def get_pose_gallery():
    """Retourne toutes les poses sauvegardées de l'utilisateur courant."""
    try:
        supabase = get_supabase()
        result = (
            supabase.table("pose_gallery")
            .select("*")
            .eq("user_id", POSE_GALLERY_USER_ID)
            .execute()
        )
        poses = []
        for row in result.data:
            signed_url = await visual_agent.get_pose_signed_url(row["storage_path"])
            poses.append(
                PoseItem(
                    id=row["id"],
                    pose_key=row["pose_key"],
                    image_url=signed_url,
                    storage_path=row["storage_path"],
                    created_at=row["created_at"],
                )
            )
        return {"poses": poses}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/poses/save", response_model=SavePoseResponse)
async def save_pose(request: SavePoseRequest):
    """Sauvegarde une pose générée dans Supabase Storage + DB."""
    try:
        supabase = get_supabase()

        save_result = await visual_agent.save_pose_to_storage(
            image_url=request.image_url,
            pose_key=request.pose_key,
            user_id=POSE_GALLERY_STORAGE_PREFIX,
        )
        storage_path = save_result["storage_path"]

        supabase.table("pose_gallery").upsert(
            {
                "user_id": POSE_GALLERY_USER_ID,
                "pose_key": request.pose_key,
                "image_url": storage_path,
                "storage_path": storage_path,
            },
            on_conflict="user_id,pose_key",
        ).execute()

        return SavePoseResponse(
            success=True,
            pose_key=request.pose_key,
            storage_path=storage_path,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/poses/{pose_key}")
async def delete_pose(pose_key: str):
    """Supprime une pose du Storage et de la DB."""
    try:
        supabase = get_supabase()

        result = (
            supabase.table("pose_gallery")
            .select("storage_path")
            .eq("pose_key", pose_key)
            .eq("user_id", POSE_GALLERY_USER_ID)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Pose non trouvée")

        storage_path = result.data[0]["storage_path"]

        await visual_agent.delete_pose_from_storage(storage_path)

        supabase.table("pose_gallery").delete().eq("pose_key", pose_key).eq(
            "user_id", POSE_GALLERY_USER_ID
        ).execute()

        return {"success": True, "pose_key": pose_key}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

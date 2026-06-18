# ============================================
# VIDEO ROUTER — CyberForge
# Routes API Video Builder
# ============================================

import os
import uuid
import asyncio
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import Optional
from supabase import create_client

from services.kling_service import kling_service
from services.video_assembly import video_assembly
from agents.video_ai import video_ai

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/video", tags=["video"])

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)


# ─────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────

class GenerateScenesRequest(BaseModel):
    brand: str
    brief: str
    ambiance: Optional[str] = "cinématique premium"
    slogan: Optional[str] = ""
    key_message: Optional[str] = ""
    call_to_action: Optional[str] = ""
    secteur: Optional[str] = ""
    ton: Optional[str] = "professionnel"
    nb_scenes: Optional[int] = 6

class CreateProjectRequest(BaseModel):
    title: str
    brand: str
    brief: str
    ambiance: Optional[str] = "cinématique premium"
    scenes: list

class StartGenerationRequest(BaseModel):
    project_id: str
    music_id: Optional[str] = None

class RefineSceneRequest(BaseModel):
    scene: dict
    instruction: str

class RechargeRequest(BaseModel):
    units: int


# ─────────────────────────────────────────
# ROUTES SCÈNES
# ─────────────────────────────────────────

@router.post("/scenes/generate")
async def generate_scenes(req: GenerateScenesRequest):
    """VideoAI génère 6 scènes cinématiques."""
    try:
        scenes_data = await video_ai.generate_scenes(
            brand=req.brand,
            brief=req.brief,
            ambiance=req.ambiance,
            slogan=req.slogan or "",
            key_message=req.key_message or "",
            call_to_action=req.call_to_action or "",
            secteur=req.secteur or "",
            ton=req.ton or "professionnel",
            nb_scenes=req.nb_scenes or 6,
        )
        return {"success": True, "data": scenes_data}
    except Exception as e:
        logger.error(f"generate_scenes error: {e}")
        raise HTTPException(500, str(e))


@router.post("/scenes/refine")
async def refine_scene(req: RefineSceneRequest):
    """Affine un prompt de scène."""
    try:
        refined = await video_ai.refine_scene(req.scene, req.instruction)
        return {"success": True, "data": refined}
    except Exception as e:
        raise HTTPException(500, str(e))


# ─────────────────────────────────────────
# ROUTES PROJETS
# ─────────────────────────────────────────

@router.post("/projects")
async def create_project(req: CreateProjectRequest):
    """Crée un projet vidéo avec ses clips."""
    try:
        project_id = str(uuid.uuid4())

        # Créer projet
        project = supabase.table("video_projects").insert({
            "id": project_id,
            "title": req.title,
            "brand": req.brand,
            "brief": req.brief,
            "ambiance": req.ambiance,
            "scenes": req.scenes,
            "status": "draft"
        }).execute()

        # Créer clips
        clips = []
        for scene in req.scenes:
            clip_id = str(uuid.uuid4())
            clips.append({
                "id": clip_id,
                "project_id": project_id,
                "scene_number": scene["scene_number"],
                "title": scene.get("title", ""),
                "prompt": scene["prompt"],
                "camera_move": scene.get("camera_move", ""),
                "mood": scene.get("mood", ""),
                "status": "pending"
            })

        supabase.table("video_clips").insert(clips).execute()

        return {"success": True, "project_id": project_id}

    except Exception as e:
        logger.error(f"create_project error: {e}")
        raise HTTPException(500, str(e))


@router.get("/projects")
async def get_projects():
    """Liste tous les projets vidéo."""
    try:
        result = supabase.table("video_projects")\
            .select("*")\
            .order("created_at", desc=True)\
            .execute()
        return {"success": True, "data": result.data}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Détail d'un projet avec ses clips."""
    try:
        project = supabase.table("video_projects")\
            .select("*")\
            .eq("id", project_id)\
            .single()\
            .execute()

        clips = supabase.table("video_clips")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("scene_number")\
            .execute()

        return {
            "success": True,
            "data": {
                **project.data,
                "clips": clips.data
            }
        }
    except Exception as e:
        raise HTTPException(500, str(e))


# ─────────────────────────────────────────
# GÉNÉRATION VIDÉO — SSE
# ─────────────────────────────────────────

@router.post("/generate")
async def start_generation(req: StartGenerationRequest):
    """Lance la génération complète en SSE temps réel."""

    async def event_stream():
        try:
            project_id = req.project_id

            # Récupérer clips pending
            clips_result = supabase.table("video_clips")\
                .select("*")\
                .eq("project_id", project_id)\
                .eq("status", "pending")\
                .order("scene_number")\
                .execute()

            clips = clips_result.data

            if not clips:
                yield f"data: {{'type':'error','message':'Aucun clip à générer'}}\n\n"
                return

            # Mettre à jour statut projet
            supabase.table("video_projects").update({
                "status": "generating"
            }).eq("id", project_id).execute()

            yield f"data: {{'type':'start','total':{len(clips)}}}\n\n"

            clip_paths = []

            # Générer chaque clip séquentiellement
            for i, clip in enumerate(clips):
                yield f"data: {{'type':'clip_start','scene':{clip['scene_number']},'title':'{clip['title']}'}}\n\n"

                # Soumettre à Kling
                result = await kling_service.generate_clip(
                    project_id=project_id,
                    clip_id=clip["id"],
                    prompt=clip["prompt"],
                    scene_number=clip["scene_number"]
                )

                yield f"data: {{'type':'clip_processing','scene':{clip['scene_number']},'task_id':'{result['task_id']}'}}\n\n"

                # Attendre génération
                clip_url = await kling_service.wait_for_clip(
                    task_id=result["task_id"],
                    clip_id=clip["id"]
                )

                # Télécharger clip
                filename = f"{project_id}_scene_{clip['scene_number']}.mp4"
                clip_path = await video_assembly.download_clip(clip_url, filename)
                clip_paths.append(clip_path)

                yield f"data: {{'type':'clip_done','scene':{clip['scene_number']},'progress':{i+1}}}\n\n"

            # Assemblage final
            yield f"data: {{'type':'assembling'}}\n\n"

            supabase.table("video_projects").update({
                "status": "assembling"
            }).eq("id", project_id).execute()

            # Récupérer musique si sélectionnée
            music_path = None
            if req.music_id:
                music_result = supabase.table("video_music_library")\
                    .select("*")\
                    .eq("id", req.music_id)\
                    .single()\
                    .execute()
                if music_result.data:
                    music_url = music_result.data.get("url", "")
                    if music_url:
                        music_path = Path("static") / music_url.lstrip("/")

            final_path = await video_assembly.assemble_clips(
                project_id=project_id,
                clip_paths=clip_paths,
                music_path=music_path
            )

            project_data = supabase.table("video_projects")\
                .select("brand, title")\
                .eq("id", project_id)\
                .single()\
                .execute()
            brand_name = project_data.data.get("brand", "CyberForge")

            overlay_path = Path(f"static/videos/{project_id}_final_branded.mp4")
            await video_assembly.add_text_overlay(
                video_path=final_path,
                brand_name=brand_name.upper(),
                tagline="Powered by CyberForge AI",
                output_path=overlay_path
            )

            # URL publique
            final_url = f"/static/videos/{project_id}_final_branded.mp4"

            # Mettre à jour projet
            supabase.table("video_projects").update({
                "status": "done",
                "final_video_url": final_url
            }).eq("id", project_id).execute()

            # Nettoyage temp
            await video_assembly.cleanup_project(project_id)

            yield f"data: {{'type':'done','url':'{final_url}','project_id':'{project_id}'}}\n\n"

        except Exception as e:
            logger.error(f"Generation error: {e}")
            supabase.table("video_projects").update({
                "status": "failed"
            }).eq("id", req.project_id).execute()
            yield f"data: {{'type':'error','message':'{str(e)}'}}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


# ─────────────────────────────────────────
# SOLDE KLING
# ─────────────────────────────────────────

@router.get("/balance")
async def get_balance():
    """Retourne le solde Kling actuel."""
    try:
        balance = await kling_service.get_balance()
        return {"success": True, "data": balance}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/balance/recharge")
async def recharge_balance(req: RechargeRequest):
    """Met à jour le solde après rechargement manuel."""
    try:
        updated = await kling_service.recharge_balance(req.units)
        return {"success": True, "data": updated}
    except Exception as e:
        raise HTTPException(500, str(e))


# ─────────────────────────────────────────
# MUSIQUE
# ─────────────────────────────────────────

@router.get("/music")
async def get_music_library():
    """Liste la bibliothèque musicale."""
    try:
        result = supabase.table("video_music_library")\
            .select("*")\
            .order("name")\
            .execute()
        return {"success": True, "data": result.data}
    except Exception as e:
        raise HTTPException(500, str(e))


# ─────────────────────────────────────────
# TÉLÉCHARGEMENT VIDÉO FINALE
# ─────────────────────────────────────────

@router.get("/download/{project_id}")
async def download_final_video(project_id: str):
    """Télécharge la vidéo finale assemblée (version brandée si disponible)."""
    try:
        branded_path = Path(f"static/videos/{project_id}_final_branded.mp4")
        normal_path = Path(f"static/videos/{project_id}_final.mp4")

        if branded_path.exists():
            path = branded_path
        elif normal_path.exists():
            path = normal_path
        else:
            raise HTTPException(404, "Vidéo non trouvée")

        return FileResponse(
            path,
            media_type="video/mp4",
            filename=f"cyberforge-pub-{project_id[:8]}.mp4"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

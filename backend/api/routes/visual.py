"""Routes VisualAI — /api/visual/*"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from agents.visual_agent import visual_agent

router = APIRouter(prefix="/api/visual", tags=["visual"])


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
async def generate_social_visual(body: SocialVisualRequest):
    result = await visual_agent.generate_social_visual(
        texte_principal=body.texte_principal,
        sous_texte=body.sous_texte,
        format_key=body.format_key,
        style=body.style,
        pose_key=body.pose_key,
        sujet_context=body.sujet_context,
    )
    if "error" in result:
        return {"success": False, "error": result["error"]}
    return {"success": True, **result}

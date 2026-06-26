"""Routes ContentAI — /api/content/*"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from agents.content_agent import content_agent

router = APIRouter(prefix="/api/content", tags=["content"])


class PostRequest(BaseModel):
    sujet: str = Field(..., min_length=3, max_length=500)
    secteur: str = Field(..., min_length=2, max_length=100)
    format_reseau: str = Field(..., pattern="^(linkedin|instagram|tiktok|twitter)$")
    ton_personnalise: str = Field(default="", max_length=100)
    nom_entreprise: str = Field(default="", max_length=100)


class HashtagsRequest(BaseModel):
    sujet: str = Field(..., min_length=3, max_length=500)
    secteur: str = Field(..., min_length=2, max_length=100)
    format_reseau: str = Field(..., pattern="^(linkedin|instagram|tiktok|twitter)$")
    nb_hashtags: int = Field(default=10, ge=5, le=20)


class BioRequest(BaseModel):
    nom_entreprise: str = Field(..., min_length=2, max_length=100)
    secteur: str = Field(..., min_length=2, max_length=100)
    valeur_ajoutee: str = Field(..., min_length=5, max_length=300)
    format_reseau: str = Field(..., pattern="^(linkedin|instagram|tiktok|twitter)$")


# — Modèles Mode CapCore —
class CapcorePostRequest(BaseModel):
    sujet_type: str
    format_reseau: str = Field(
        pattern="^(linkedin|instagram|tiktok|twitter)$"
    )
    angle: str = ""


@router.get("/formats")
async def get_formats():
    return {"formats": content_agent.get_formats(), "secteurs": content_agent.get_secteurs()}


@router.post("/post")
async def generate_post(body: PostRequest):
    try:
        result = await content_agent.generate_post(
            sujet=body.sujet,
            secteur=body.secteur,
            format_reseau=body.format_reseau,
            ton_personnalise=body.ton_personnalise,
            nom_entreprise=body.nom_entreprise,
        )
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/hashtags")
async def generate_hashtags(body: HashtagsRequest):
    try:
        result = await content_agent.generate_hashtags(
            sujet=body.sujet,
            secteur=body.secteur,
            format_reseau=body.format_reseau,
            nb_hashtags=body.nb_hashtags,
        )
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/bio")
async def generate_bio(body: BioRequest):
    try:
        result = await content_agent.generate_bio(
            nom_entreprise=body.nom_entreprise,
            secteur=body.secteur,
            valeur_ajoutee=body.valeur_ajoutee,
            format_reseau=body.format_reseau,
        )
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}


# — Routes Mode CapCore —
@router.get("/capcore-subjects")
def get_capcore_subjects():
    return {"subjects": content_agent.get_capcore_subjects()}


@router.post("/capcore-post")
async def generate_capcore_post(body: CapcorePostRequest):
    result = await content_agent.generate_capcore_post(
        sujet_type=body.sujet_type,
        format_reseau=body.format_reseau,
        angle=body.angle,
    )
    if "error" in result and "post" not in result:
        return {"success": False, "error": result["error"]}
    return {"success": True, **result}

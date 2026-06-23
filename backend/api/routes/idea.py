"""
IdeaAI Router — CyberForge
Endpoints pour le générateur d'idées créatives.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.idea_agent import idea_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/idea", tags=["idea"])


class MarketingIdeaRequest(BaseModel):
    sector: str
    target: str
    context: str = ""
    count: int = Field(default=8, ge=1, le=20)


class ProductIdeaRequest(BaseModel):
    sector: str
    target: str
    budget: str = "medium"
    context: str = ""
    count: int = Field(default=8, ge=1, le=20)


@router.post("/marketing")
async def generate_marketing_ideas(request: MarketingIdeaRequest) -> dict:
    """Génère des idées pub/marketing injectables dans Video Builder."""
    try:
        result = await idea_agent.generate_marketing_ideas(
            sector=request.sector,
            target=request.target,
            context=request.context,
            count=request.count,
        )
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("IdeaAI marketing error")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/product")
async def generate_product_ideas(request: ProductIdeaRequest) -> dict:
    """Génère des idées de produits digitaux lançables dans CyberForge."""
    try:
        result = await idea_agent.generate_product_ideas(
            sector=request.sector,
            target=request.target,
            budget=request.budget,
            context=request.context,
            count=request.count,
        )
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("IdeaAI product error")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/sectors")
async def get_sectors() -> dict[str, list[str]]:
    """Liste des secteurs disponibles pour guider l'utilisateur."""
    return {
        "sectors": [
            "Artisanat & BTP",
            "Restauration & Food",
            "Beauté & Bien-être",
            "Santé & Medical",
            "Immobilier",
            "E-commerce & Retail",
            "Sport & Fitness",
            "Education & Formation",
            "Finance & Comptabilité",
            "Transport & Logistique",
            "Tourisme & Hôtellerie",
            "Tech & SaaS",
            "Marketing & Communication",
            "Juridique & Conseil",
            "Agriculture & Nature",
            "Mode & Lifestyle",
            "Musique & Arts",
            "Associations & ONG",
        ]
    }

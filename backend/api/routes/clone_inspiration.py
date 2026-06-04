"""
POST /api/clone-inspiration — clone & améliore (Firecrawl + Claude Haiku).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, HttpUrl

from config import get_settings
from tools.firecrawl_client import FirecrawlError
from tools.inspiration_analysis import ScrapeSectionOut, clone_inspiration_site

router = APIRouter(tags=["inspiration"])


class CloneInspirationRequest(BaseModel):
    url: HttpUrl
    project_type: str = Field(
        default="vitrine",
        max_length=64,
        description="Type de projet (vitrine, site_reservation, ecommerce, …)",
    )
    client_name: str = Field(min_length=1, max_length=120)


class CloneInspirationResponse(BaseModel):
    url: str
    title: str | None = None
    company_name: str
    client_name: str
    secteur: str
    sector_label: str | None = None
    project_type: str
    description: str
    services: list[str] = Field(default_factory=list)
    couleur_primaire: str
    couleur_secondaire: str
    ville: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    brief_builder: str
    palette: dict[str, str] = Field(default_factory=dict)
    sections: list[ScrapeSectionOut] = Field(default_factory=list)
    screenshot_url: str | None = None


@router.post("/clone-inspiration", response_model=CloneInspirationResponse)
async def clone_inspiration(body: CloneInspirationRequest) -> CloneInspirationResponse:
    settings = get_settings()
    if not settings.firecrawl_configured:
        raise HTTPException(
            status_code=503,
            detail="FIRECRAWL_API_KEY non configurée.",
        )

    try:
        data = await clone_inspiration_site(
            str(body.url),
            project_type=body.project_type.strip(),
            client_name=body.client_name.strip(),
            settings=settings,
        )
    except FirecrawlError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    sections = [ScrapeSectionOut.model_validate(row) for row in data.get("sections") or []]
    return CloneInspirationResponse(
        url=data["url"],
        title=data.get("title"),
        company_name=data["company_name"],
        client_name=data["client_name"],
        secteur=data["secteur"],
        sector_label=data.get("sector_label"),
        project_type=data["project_type"],
        description=data["description"],
        services=data.get("services") or [],
        couleur_primaire=data["couleur_primaire"],
        couleur_secondaire=data["couleur_secondaire"],
        ville=data.get("ville") or "",
        phone=data.get("phone") or "",
        email=data.get("email") or "",
        address=data.get("address") or "",
        brief_builder=data["brief_builder"],
        palette=data.get("palette") or {},
        sections=sections,
        screenshot_url=data.get("screenshot_url"),
    )

"""
POST /api/scrape-inspiration — analyse légère d'une URL d'inspiration (Firecrawl).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, HttpUrl

from config import get_settings
from tools.firecrawl_client import FirecrawlError
from tools.inspiration_analysis import scrape_inspiration_url

router = APIRouter(tags=["inspiration"])


class ScrapeInspirationRequest(BaseModel):
    url: HttpUrl


class ScrapeInspirationResponse(BaseModel):
    title: str | None = None
    description: str | None = None
    primary_color: str | None = None
    screenshot_url: str | None = None


@router.post("/scrape-inspiration", response_model=ScrapeInspirationResponse)
async def scrape_inspiration(body: ScrapeInspirationRequest) -> ScrapeInspirationResponse:
    settings = get_settings()
    if not settings.firecrawl_configured:
        raise HTTPException(
            status_code=503,
            detail="FIRECRAWL_API_KEY non configurée.",
        )
    try:
        data = await scrape_inspiration_url(str(body.url), settings=settings)
    except FirecrawlError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return ScrapeInspirationResponse(
        title=data.get("title"),
        description=data.get("description"),
        primary_color=data.get("primary_color"),
        screenshot_url=data.get("screenshot_url"),
    )

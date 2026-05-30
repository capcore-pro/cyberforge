"""
Firecrawl — scrape concurrent, analyse DeepSeek et brief BuilderAI.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, HttpUrl

from config import get_settings
from security.llm_secrets import get_effective_llm_key, get_effective_llm_key_for_http
from tools.codegen_service import _parse_json_response, _utf8_json_body
from tools.firecrawl_client import FirecrawlError, ScrapeResult, firecrawl_scrape
from tools.toolbox_media import search_toolbox_photos
from tools.toolbox_sectors import SECTEURS, get_sector_bundle, normalize_sector_key

logger = logging.getLogger(__name__)

router = APIRouter(tags=["firecrawl"])

DEEPSEEK_CHAT_URL = "https://api.deepseek.com/chat/completions"

_PLACEHOLDER_RE = re.compile(
    r"\b(?:https?://|www\.)[^\s<>'\"]+|"
    r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b|"
    r"\b(?:\+?\d[\d\s().-]{7,}\d)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Modèles
# ---------------------------------------------------------------------------


class ScrapeRequest(BaseModel):
    url: HttpUrl
    include_images: bool = True


class ScrapeSectionOut(BaseModel):
    type: str
    heading: str | None = None
    summary: str | None = None


class ScrapeResponse(BaseModel):
    url: str
    title: str | None = None
    meta_description: str | None = None
    sections: list[ScrapeSectionOut] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    cta_texts: list[str] = Field(default_factory=list)
    couleurs: dict[str, str] = Field(default_factory=dict)
    titres: list[str] = Field(default_factory=list)
    descriptions: list[str] = Field(default_factory=list)
    temoignages: list[str] = Field(default_factory=list)


class AnalyzeCompetitorRequest(BaseModel):
    url: HttpUrl
    secteur: str = Field(min_length=1, max_length=40)


class AnalyzeCompetitorResponse(BaseModel):
    url: str
    secteur: str
    analyse: str
    points_forts: list[str] = Field(default_factory=list)
    points_faibles: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    composants_recommandes: list[str] = Field(default_factory=list)


class CloneInspirationRequest(BaseModel):
    url: HttpUrl
    secteur: str = Field(min_length=1, max_length=40)
    nom_client: str = Field(min_length=1, max_length=120)


class CloneImageReplacement(BaseModel):
    source_url: str
    stock_url: str | None = None
    stock_source: str | None = None
    query: str | None = None


class CloneInspirationResponse(BaseModel):
    url: str
    secteur: str
    nom_client: str
    brief_builder: str
    palette: dict[str, str]
    sections: list[ScrapeSectionOut]
    placeholders: dict[str, str]
    images: list[CloneImageReplacement] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _scrape_to_response(result: ScrapeResult) -> ScrapeResponse:
    return ScrapeResponse(
        url=result.url,
        title=result.title,
        meta_description=result.meta_description,
        sections=[
            ScrapeSectionOut(
                type=s.type,
                heading=s.heading,
                summary=s.summary,
            )
            for s in result.sections
        ],
        images=[img.url for img in result.images],
        cta_texts=result.cta_texts,
        couleurs=result.couleurs,
        titres=result.titres,
        descriptions=result.descriptions,
        temoignages=result.temoignages,
    )


async def _call_deepseek_json(*, system: str, user: str) -> dict[str, Any]:
    settings = get_settings()
    api_key = get_effective_llm_key("DEEPSEEK_API_KEY", settings)
    if not api_key:
        raise HTTPException(status_code=503, detail="DEEPSEEK_API_KEY manquante.")

    body, content_headers = _utf8_json_body(
        {
            "model": settings.coremind_deepseek_model,
            "temperature": 0.35,
            "max_tokens": min(settings.coremind_max_output_tokens, 2048),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
    )
    timeout = httpx.Timeout(settings.coremind_llm_timeout_seconds, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            DEEPSEEK_CHAT_URL,
            headers={
                "Authorization": f"Bearer {get_effective_llm_key_for_http('DEEPSEEK_API_KEY', settings) or api_key}",
                **content_headers,
            },
            content=body,
        )

    if response.status_code >= 400:
        snippet = response.content.decode("utf-8", errors="replace")[:400]
        raise HTTPException(
            status_code=502, detail=f"DeepSeek HTTP {response.status_code}: {snippet}"
        )

    payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    if not str(content).strip():
        raise HTTPException(status_code=502, detail="Réponse DeepSeek vide.")
    return _parse_json_response(str(content))


def _as_str_list(raw: Any, *, limit: int = 12) -> list[str]:
    if isinstance(raw, str):
        parts = [p.strip() for p in re.split(r"[\n;]", raw) if p.strip()]
    elif isinstance(raw, list):
        parts = [str(p).strip() for p in raw if str(p).strip()]
    else:
        parts = []
    return parts[:limit]


def _sector_palette(secteur: str, detected: dict[str, str]) -> dict[str, str]:
    bundle = get_sector_bundle(secteur)
    palette: dict[str, str] = {}
    if bundle:
        palette.update(bundle.palette)
    for key, val in detected.items():
        if val.startswith("#"):
            palette[key] = val
    if not palette and bundle:
        palette = dict(bundle.palette)
    return palette


def _placeholderize(text: str, nom_client: str) -> str:
    cleaned = _PLACEHOLDER_RE.sub("{{CONTACT}}", text)
    if nom_client and nom_client.lower() in cleaned.lower():
        cleaned = re.sub(re.escape(nom_client), "{{NOM_CLIENT}}", cleaned, flags=re.I)
    return cleaned


def _build_placeholders(result: ScrapeResult, nom_client: str) -> dict[str, str]:
    placeholders: dict[str, str] = {
        "nom_client": "{{NOM_CLIENT}}",
        "titre_page": "{{TITRE_PAGE}}",
        "meta_description": "{{META_DESCRIPTION}}",
    }
    for index, title in enumerate(result.titres[:8], start=1):
        placeholders[f"titre_{index}"] = _placeholderize(title, nom_client)
    for index, desc in enumerate(result.descriptions[:6], start=1):
        placeholders[f"description_{index}"] = _placeholderize(desc, nom_client)
    for index, cta in enumerate(result.cta_texts[:8], start=1):
        placeholders[f"cta_{index}"] = _placeholderize(cta, nom_client)
    for index, quote in enumerate(result.temoignages[:6], start=1):
        placeholders[f"temoignage_{index}"] = _placeholderize(quote, nom_client)
    if result.title:
        placeholders["titre_page"] = _placeholderize(result.title, nom_client)
    if result.meta_description:
        placeholders["meta_description"] = _placeholderize(
            result.meta_description, nom_client
        )
    return placeholders


async def _stock_replacements(
    result: ScrapeResult,
    secteur: str,
) -> list[CloneImageReplacement]:
    bundle = get_sector_bundle(secteur)
    default_query = (
        bundle.mots_cles_visuels[0]
        if bundle and bundle.mots_cles_visuels
        else "business"
    )
    replacements: list[CloneImageReplacement] = []
    _, pool = await search_toolbox_photos(default_query, secteur=secteur, per_page=12)
    pool_index = 0

    for image in result.images[:10]:
        query = default_query
        if image.role == "hero":
            query = bundle.mots_cles_visuels[0] if bundle else default_query
        effective_query, photos = await search_toolbox_photos(
            query, secteur=secteur, per_page=4
        )
        pick = photos[0] if photos else (pool[pool_index % len(pool)] if pool else None)
        pool_index += 1
        replacements.append(
            CloneImageReplacement(
                source_url=image.url,
                stock_url=pick.url_full if pick else None,
                stock_source=pick.source if pick else None,
                query=effective_query,
            )
        )
    return replacements


def _build_brief_builder(
    *,
    result: ScrapeResult,
    nom_client: str,
    secteur: str,
    palette: dict[str, str],
    placeholders: dict[str, str],
    images: list[CloneImageReplacement],
) -> str:
    lines = [
        f"# Brief BuilderAI — inspiration {result.url}",
        f"Client cible : {nom_client}",
        f"Secteur toolbox : {normalize_sector_key(secteur)}",
        "",
        "## Palette",
    ]
    for key, val in palette.items():
        lines.append(f"- {key}: {val}")
    lines.extend(["", "## Structure (ordre des sections)"])
    for index, section in enumerate(result.sections, start=1):
        heading = section.heading or section.type
        summary = section.summary or ""
        lines.append(f"{index}. **{section.type}** — {heading}")
        if summary:
            lines.append(f"   - {summary[:200]}")
    lines.extend(["", "## Placeholders texte"])
    for key, val in placeholders.items():
        lines.append(f"- `{key}`: {val[:160]}")
    lines.extend(["", "## Images (remplacement stock)"])
    for row in images:
        stock = row.stock_url or "(aucun stock trouvé)"
        lines.append(
            f"- Source: {row.source_url[:80]}… → {stock} ({row.stock_source or 'n/a'})"
        )
    lines.extend(
        [
            "",
            "## Consignes BuilderAI",
            "- Reproduire la structure et le rythme visuel du site source.",
            "- Utiliser la palette ci-dessus (variables CSS).",
            "- Remplacer tous les textes par les placeholders fournis.",
            "- Utiliser les URLs stock pour les visuels hero et sections.",
            "- Prioriser shadcn/ui + Framer Motion pour les blocs interactifs.",
        ]
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/firecrawl/scrape", response_model=ScrapeResponse)
async def scrape_site(body: ScrapeRequest) -> ScrapeResponse:
    """Scrape une URL via Firecrawl et retourne textes, images, sections et couleurs."""
    try:
        result = await firecrawl_scrape(
            str(body.url),
            include_images=body.include_images,
        )
    except FirecrawlError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return _scrape_to_response(result)


@router.post("/firecrawl/analyze-competitor", response_model=AnalyzeCompetitorResponse)
async def analyze_competitor(body: AnalyzeCompetitorRequest) -> AnalyzeCompetitorResponse:
    """Scrape un concurrent puis analyse DeepSeek (forces, faiblesses, suggestions)."""
    secteur_key = normalize_sector_key(body.secteur)
    if secteur_key not in SECTEURS:
        raise HTTPException(status_code=404, detail=f"Secteur inconnu : {body.secteur}")

    try:
        scraped = await firecrawl_scrape(str(body.url), include_images=True)
    except FirecrawlError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    summary_block = {
        "url": scraped.url,
        "title": scraped.title,
        "meta_description": scraped.meta_description,
        "sections": [s.model_dump() for s in scraped.sections],
        "cta_texts": scraped.cta_texts,
        "temoignages": scraped.temoignages,
        "couleurs": scraped.couleurs,
        "titres": scraped.titres[:10],
        "descriptions": scraped.descriptions[:8],
    }
    system = (
        "Tu es un consultant UX/conversion pour CyberForge. "
        "Analyse le site concurrent fourni et réponds UNIQUEMENT en JSON valide avec les clés : "
        "analyse (string, 2-4 phrases), points_forts (array of strings), "
        "points_faibles (array of strings), suggestions (array of strings), "
        "composants_recommandes (array of strings — blocs UI type hero, pricing, testimonials…)."
    )
    user = (
        f"Secteur cible : {secteur_key}.\n"
        f"Données extraites :\n{summary_block}\n"
        f"Extrait markdown (tronqué) :\n{(scraped.markdown or '')[:8000]}"
    )

    data = await _call_deepseek_json(system=system, user=user)
    return AnalyzeCompetitorResponse(
        url=scraped.url,
        secteur=secteur_key,
        analyse=str(data.get("analyse") or "").strip(),
        points_forts=_as_str_list(data.get("points_forts")),
        points_faibles=_as_str_list(data.get("points_faibles")),
        suggestions=_as_str_list(data.get("suggestions")),
        composants_recommandes=_as_str_list(data.get("composants_recommandes")),
    )


@router.post("/firecrawl/clone-inspiration", response_model=CloneInspirationResponse)
async def clone_inspiration(body: CloneInspirationRequest) -> CloneInspirationResponse:
    """
    Scrape une inspiration, détecte structure/style et produit un brief BuilderAI
    avec placeholders et images stock Pexels/Unsplash.
    """
    secteur_key = normalize_sector_key(body.secteur)
    if secteur_key not in SECTEURS:
        raise HTTPException(status_code=404, detail=f"Secteur inconnu : {body.secteur}")

    try:
        scraped = await firecrawl_scrape(str(body.url), include_images=True)
    except FirecrawlError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    palette = _sector_palette(secteur_key, scraped.couleurs)
    placeholders = _build_placeholders(scraped, body.nom_client.strip())
    images = await _stock_replacements(scraped, secteur_key)
    brief = _build_brief_builder(
        result=scraped,
        nom_client=body.nom_client.strip(),
        secteur=secteur_key,
        palette=palette,
        placeholders=placeholders,
        images=images,
    )

    return CloneInspirationResponse(
        url=scraped.url,
        secteur=secteur_key,
        nom_client=body.nom_client.strip(),
        brief_builder=brief,
        palette=palette,
        sections=[
            ScrapeSectionOut(type=s.type, heading=s.heading, summary=s.summary)
            for s in scraped.sections
        ],
        placeholders=placeholders,
        images=images,
    )

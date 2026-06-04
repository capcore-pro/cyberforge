"""
Analyse de sites d'inspiration — Firecrawl, couleurs CSS dominantes, extraction Haiku.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections import Counter
from typing import Any
from urllib.parse import urlparse

import anthropic
from pydantic import BaseModel

from config import Settings, get_settings
from security.llm_secrets import get_effective_llm_key
from tools.codegen_service import _parse_json_response
from tools.firecrawl_client import FirecrawlError, ScrapeResult, firecrawl_scrape
from tools.toolbox_sectors import SECTEURS, get_sector_bundle, normalize_sector_key

logger = logging.getLogger(__name__)

_HEX_COLOR_RE = re.compile(r"#[0-9A-Fa-f]{3,8}\b")
_STYLE_BLOCK_RE = re.compile(
    r"<style[^>]*>(.*?)</style>",
    re.IGNORECASE | re.DOTALL,
)
_INLINE_STYLE_RE = re.compile(
    r'\bstyle=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_SKIP_HEX = frozenset(
    {
        "#fff",
        "#ffffff",
        "#000",
        "#000000",
        "#111",
        "#111111",
        "#222",
        "#333",
        "#444",
        "#555",
        "#666",
        "#777",
        "#888",
        "#999",
        "#aaa",
        "#bbb",
        "#ccc",
        "#ddd",
        "#eee",
        "#fafafa",
        "#f5f5f5",
        "#f8f8f8",
        "#transparent",
    }
)

COLOR_LUMINANCE_MAX = 200
CAMPING_PRIMARY_FALLBACK = "#2d6a4f"
CAMPING_SECONDARY_FALLBACK = "#1b4332"

HAIKU_EXTRACT_SYSTEM = """Tu analyses un site web scrapé pour CyberForge (générateur de sites PME françaises).
Réponds UNIQUEMENT en JSON valide (sans markdown) avec les clés :
- company_name (string, nom de l'entreprise déduit)
- secteur (string, secteur d'activité en français, ex: "restauration", "camping / plein air")
- description (string, 2-4 phrases décrivant l'activité)
- services (array of strings, 4-8 prestations/produits)
- couleur_primaire (string hex #RRGGBB)
- couleur_secondaire (string hex #RRGGBB)
- ville (string ou "")
- phone (string ou "")
- email (string ou "")
- address (string ou "")
Couleurs de marque : choisis des hex SATURÉS et LISIBLES (pas blanc, crème, gris clair).
La luminosité perçue de couleur_primaire doit rester sous 200 (couleur assez foncée pour navbar/CTA).
Pour camping / plein air / hébergement : verts nature (#2d6a4f, #1b4332) si le site source est trop clair.
Texte en français."""


class ScrapeSectionOut(BaseModel):
    type: str
    heading: str | None = None
    summary: str | None = None


def _normalize_hex(hex_color: str) -> str:
    raw = hex_color.strip().lower()
    if len(raw) == 4 and raw.startswith("#"):
        return "#" + "".join(c * 2 for c in raw[1:])
    return raw


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = _normalize_hex(hex_color).lstrip("#")
    if len(h) != 6:
        return 0, 0, 0
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def color_luminance(hex_color: str) -> float:
    """Luminosité perçue 0–255 (formule standard)."""
    r, g, b = _hex_to_rgb(hex_color)
    return 0.299 * r + 0.587 * g + 0.114 * b


def is_color_too_light(hex_color: str, *, threshold: float = COLOR_LUMINANCE_MAX) -> bool:
    if not hex_color or not str(hex_color).strip().startswith("#"):
        return True
    return color_luminance(hex_color) > threshold


def _is_camping_sector(secteur: str) -> bool:
    low = (secteur or "").lower()
    return any(
        token in low
        for token in ("camping", "plein air", "hebergement", "hébergement", "lodging")
    )


def _sector_fallback_primary(secteur: str) -> str:
    if _is_camping_sector(secteur):
        return CAMPING_PRIMARY_FALLBACK
    bundle = get_sector_bundle(normalize_sector_key(secteur))
    if bundle and bundle.palette.get("primary"):
        primary = bundle.palette["primary"]
        if not is_color_too_light(primary):
            return primary
    return "#1a5276"


def _sector_fallback_secondary(secteur: str) -> str:
    if _is_camping_sector(secteur):
        return CAMPING_SECONDARY_FALLBACK
    bundle = get_sector_bundle(normalize_sector_key(secteur))
    if bundle and bundle.palette.get("secondary"):
        secondary = bundle.palette["secondary"]
        if not is_color_too_light(secondary):
            return secondary
    return "#1a1a2e"


def validate_brand_hex(hex_color: str | None, *, secteur: str, role: str = "primary") -> str:
    """
    Rejette les couleurs trop claires (luminosité > 200).
    Camping → #2d6a4f ; sinon palette secteur ou défaut foncé.
    """
    candidate = (hex_color or "").strip()
    if candidate.startswith("#") and not is_color_too_light(candidate):
        return _normalize_hex(candidate)
    if role == "secondary":
        return _sector_fallback_secondary(secteur)
    return _sector_fallback_primary(secteur)


def dominant_hex_colors_from_html(html: str, *, limit: int = 5) -> list[str]:
    """Compte les couleurs hex dans les blocs CSS / attributs style."""
    css_chunks: list[str] = []
    for match in _STYLE_BLOCK_RE.finditer(html or ""):
        css_chunks.append(match.group(1))
    for match in _INLINE_STYLE_RE.finditer(html or ""):
        css_chunks.append(match.group(1))
    haystack = "\n".join(css_chunks) if css_chunks else (html or "")[:80_000]
    counts: Counter[str] = Counter()
    for found in _HEX_COLOR_RE.findall(haystack):
        norm = _normalize_hex(found)
        if norm in _SKIP_HEX:
            continue
        if len(norm) not in (7, 9):
            continue
        if is_color_too_light(norm):
            continue
        counts[norm] += 1
    return [color for color, _ in counts.most_common(limit)]


def resolve_primary_secondary_colors(
    scraped: ScrapeResult,
    *,
    html: str | None = None,
) -> tuple[str | None, str | None]:
    """Couleur primaire/secondaire : branding Firecrawl puis CSS dominant."""
    primary = scraped.couleurs.get("primary")
    secondary = scraped.couleurs.get("secondary")
    if primary and secondary:
        return primary, secondary

    raw_html = html
    if raw_html is None and scraped.raw_json is not None:
        raw_html = ""
    dominant = dominant_hex_colors_from_html(raw_html or "")
    if not primary and dominant:
        primary = dominant[0]
    if not secondary and len(dominant) > 1:
        secondary = dominant[1]
    elif not secondary and scraped.couleurs.get("accent"):
        secondary = scraped.couleurs.get("accent")
    return primary, secondary


def screenshot_url_from_scrape(scraped: ScrapeResult) -> str | None:
    if scraped.images:
        hero = next((i for i in scraped.images if i.role == "hero"), None)
        if hero:
            return hero.url
        return scraped.images[0].url
    return None


def _domain_brand(url: str) -> str:
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        host = ""
    host = re.sub(r"^www\.", "", host)
    if not host:
        return "Mon projet"
    base = host.split(".")[0] if "." in host else host
    base = re.sub(r"[^a-z0-9-]+", " ", base).strip().replace("-", " ")
    return (base.title()[:80] or "Mon projet").strip()


def _sector_palette(secteur: str, detected: dict[str, str]) -> dict[str, str]:
    bundle = get_sector_bundle(secteur)
    palette: dict[str, str] = {}
    if bundle:
        palette.update(bundle.palette)
    for key, val in detected.items():
        if isinstance(val, str) and val.startswith("#"):
            palette[key] = val
    if not palette and bundle:
        palette = dict(bundle.palette)
    return palette


def _match_toolbox_sector(secteur_hint: str) -> str:
    key = normalize_sector_key(secteur_hint)
    if key in SECTEURS:
        return key
    low = secteur_hint.lower()
    for name in SECTEURS:
        if name in low or low in name:
            return name
    return key or "commerce"


async def scrape_inspiration_url(url: str, *, settings: Settings | None = None) -> dict[str, Any]:
    """Scrape léger pour le bouton Analyser."""
    scraped = await firecrawl_scrape(url, include_images=True, settings=settings)
    primary, _secondary = resolve_primary_secondary_colors(
        scraped,
        html=scraped.html or scraped.markdown or "",
    )

    description = (
        scraped.meta_description
        or (scraped.descriptions[0] if scraped.descriptions else None)
        or (scraped.sections[0].summary if scraped.sections else None)
    )
    secteur_hint = _match_toolbox_sector("commerce")
    validated_primary = validate_brand_hex(primary, secteur=secteur_hint)
    return {
        "title": scraped.title,
        "description": description,
        "primary_color": validated_primary,
        "screenshot_url": screenshot_url_from_scrape(scraped),
    }


async def _call_haiku_json(*, user_message: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    api_key = get_effective_llm_key("ANTHROPIC_API_KEY", settings)
    if not api_key:
        raise FirecrawlError("ANTHROPIC_API_KEY manquante pour l'analyse clone.")

    model = settings.coremind_haiku_model

    def _invoke() -> str:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=1200,
            system=HAIKU_EXTRACT_SYSTEM,
            messages=[{"role": "user", "content": user_message}],
        )
        parts: list[str] = []
        for block in response.content:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        return "".join(parts)

    raw = await asyncio.to_thread(_invoke)
    return _parse_json_response(raw)


def _fallback_extract(
    scraped: ScrapeResult,
    *,
    client_name: str,
    primary: str | None,
    secondary: str | None,
    secteur_hint: str = "commerce",
) -> dict[str, Any]:
    secteur = _match_toolbox_sector(secteur_hint)
    return {
        "company_name": client_name or _domain_brand(scraped.url),
        "secteur": secteur,
        "description": scraped.meta_description
        or (scraped.descriptions[0] if scraped.descriptions else "")
        or f"Site inspiré de {scraped.url}",
        "services": scraped.cta_texts[:6] or scraped.titres[:5] or ["Contact", "Devis"],
        "couleur_primaire": validate_brand_hex(primary, secteur=secteur, role="primary"),
        "couleur_secondaire": validate_brand_hex(
            secondary, secteur=secteur, role="secondary"
        ),
        "ville": "",
        "phone": "",
        "email": "",
        "address": "",
    }


def _build_brief_builder(
    *,
    result: ScrapeResult,
    nom_client: str,
    secteur: str,
    palette: dict[str, str],
) -> str:
    lines = [
        f"# Brief CyberForge — inspiration {result.url}",
        f"Client cible : {nom_client}",
        f"Secteur : {normalize_sector_key(secteur)}",
        "",
        "## Palette",
    ]
    for key, val in palette.items():
        lines.append(f"- {key}: {val}")
    lines.extend(["", "## Structure"])
    for index, section in enumerate(result.sections, start=1):
        heading = section.heading or section.type
        lines.append(f"{index}. **{section.type}** — {heading}")
        if section.summary:
            lines.append(f"   - {section.summary[:200]}")
    if result.meta_description:
        lines.extend(["", "## Meta", result.meta_description[:400]])
    lines.extend(
        [
            "",
            "## Consignes",
            "- Recréer ce site en version premium, même structure et rythme visuel.",
            "- Palette CSS ci-dessus.",
            "- Textes adaptés au client, ton professionnel français.",
        ]
    )
    return "\n".join(lines)


async def clone_inspiration_site(
    url: str,
    *,
    project_type: str,
    client_name: str,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Scrape complet + extraction Haiku pour le mode Clone & Améliore."""
    settings = settings or get_settings()
    scraped = await firecrawl_scrape(url, include_images=True, settings=settings)

    html_src = scraped.html or scraped.markdown or ""
    primary, secondary = resolve_primary_secondary_colors(scraped, html=html_src)
    if not primary or not secondary:
        dominant = dominant_hex_colors_from_html(html_src)
        if not primary and dominant:
            primary = dominant[0]
        if not secondary and len(dominant) > 1:
            secondary = dominant[1]

    summary_block = {
        "url": scraped.url,
        "title": scraped.title,
        "meta_description": scraped.meta_description,
        "project_type": project_type,
        "couleurs_detectees": scraped.couleurs,
        "couleur_primaire_hint": primary,
        "couleur_secondaire_hint": secondary,
        "sections": [s.model_dump() for s in scraped.sections],
        "titres": scraped.titres[:12],
        "descriptions": scraped.descriptions[:8],
        "cta_texts": scraped.cta_texts[:10],
    }
    user_message = (
        f"Client demandé : {client_name.strip() or _domain_brand(url)}\n"
        f"Type de projet CyberForge : {project_type}\n"
        f"Secteurs toolbox connus : {', '.join(sorted(SECTEURS.keys()))}\n\n"
        f"Données extraites :\n{json.dumps(summary_block, ensure_ascii=False, indent=2)}\n\n"
        f"Markdown (tronqué) :\n{(scraped.markdown or '')[:10_000]}"
    )

    try:
        extracted = await _call_haiku_json(user_message=user_message, settings=settings)
    except Exception as exc:
        logger.warning("Haiku clone extraction failed: %s", exc)
        extracted = _fallback_extract(
            scraped,
            client_name=client_name,
            primary=primary,
            secondary=secondary,
        )

    company = str(extracted.get("company_name") or client_name or _domain_brand(url)).strip()
    secteur_raw = str(extracted.get("secteur") or "").strip()
    secteur_key = _match_toolbox_sector(secteur_raw or "commerce")

    raw_primary = str(extracted.get("couleur_primaire") or primary or "").strip()
    raw_secondary = str(extracted.get("couleur_secondaire") or secondary or "").strip()
    couleur_primaire = validate_brand_hex(
        raw_primary if raw_primary.startswith("#") else primary,
        secteur=secteur_key,
        role="primary",
    )
    couleur_secondaire = validate_brand_hex(
        raw_secondary if raw_secondary.startswith("#") else secondary,
        secteur=secteur_key,
        role="secondary",
    )

    services_raw = extracted.get("services")
    if isinstance(services_raw, list):
        services = [str(s).strip() for s in services_raw if str(s).strip()][:12]
    elif isinstance(services_raw, str):
        services = [p.strip() for p in re.split(r"[\n;,]", services_raw) if p.strip()][:12]
    else:
        services = []

    description = str(extracted.get("description") or "").strip()
    if not description:
        description = (
            scraped.meta_description
            or (scraped.descriptions[0] if scraped.descriptions else "")
            or f"Recréation premium du site {scraped.url}"
        )

    palette = _sector_palette(
        secteur_key,
        {
            "primary": couleur_primaire,
            "secondary": couleur_secondaire,
            **{k: v for k, v in scraped.couleurs.items() if v.startswith("#")},
        },
    )
    brief_builder = _build_brief_builder(
        result=scraped,
        nom_client=company,
        secteur=secteur_key,
        palette=palette,
    )

    return {
        "url": scraped.url,
        "title": scraped.title,
        "company_name": company,
        "client_name": company,
        "secteur": secteur_key,
        "sector_label": secteur_raw or secteur_key,
        "project_type": project_type,
        "description": description,
        "services": services,
        "couleur_primaire": couleur_primaire,
        "couleur_secondaire": couleur_secondaire,
        "ville": str(extracted.get("ville") or "").strip(),
        "phone": str(extracted.get("phone") or "").strip(),
        "email": str(extracted.get("email") or "").strip(),
        "address": str(extracted.get("address") or "").strip(),
        "brief_builder": brief_builder,
        "palette": palette,
        "sections": [
            ScrapeSectionOut(type=s.type, heading=s.heading, summary=s.summary).model_dump()
            for s in scraped.sections
        ],
        "screenshot_url": screenshot_url_from_scrape(scraped),
    }

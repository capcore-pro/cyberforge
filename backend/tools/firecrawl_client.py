"""
Client Firecrawl v2 — scrape structuré pour analyse concurrentielle.
"""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from pydantic import BaseModel, Field

from config import Settings, get_settings, plain_secret_str

logger = logging.getLogger(__name__)

FIRECRAWL_API_BASE = "https://api.firecrawl.dev/v2"
DEFAULT_TIMEOUT_SECONDS = 90.0

_IMG_SRC_RE = re.compile(
    r'<img[^>]+src=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_MD_IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
_HEX_COLOR_RE = re.compile(r"#[0-9A-Fa-f]{3,8}\b")
_CTA_RE = re.compile(
    r"<(?:a|button)[^>]*>([^<]{2,120})</(?:a|button)>",
    re.IGNORECASE,
)

SECTION_ORDER = (
    "hero",
    "about",
    "services",
    "pricing",
    "testimonials",
    "contact",
    "faq",
    "other",
)

SCRAPE_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "titres": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Titres et sous-titres principaux (H1-H3).",
        },
        "descriptions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Paragraphes descriptifs importants.",
        },
        "cta_texts": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Libellés de boutons et appels à l'action.",
        },
        "temoignages": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Citations ou avis clients.",
        },
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": list(SECTION_ORDER),
                    },
                    "heading": {"type": "string"},
                    "summary": {"type": "string"},
                },
                "required": ["type"],
            },
            "description": "Sections de page détectées dans l'ordre.",
        },
    },
}

SCRAPE_JSON_PROMPT = (
    "Extrais la structure marketing du site : titres, descriptions, CTA, témoignages "
    "et sections (hero, about, services, pricing, contact, testimonials, faq, other) "
    "dans l'ordre d'apparition."
)


class FirecrawlError(RuntimeError):
    """Erreur d'appel Firecrawl."""


class ScrapeSection(BaseModel):
    type: str
    heading: str | None = None
    summary: str | None = None
    sample_texts: list[str] = Field(default_factory=list)


class ScrapeImage(BaseModel):
    url: str
    alt: str | None = None
    role: str | None = None


class ScrapeResult(BaseModel):
    url: str
    title: str | None = None
    meta_description: str | None = None
    sections: list[ScrapeSection] = Field(default_factory=list)
    images: list[ScrapeImage] = Field(default_factory=list)
    cta_texts: list[str] = Field(default_factory=list)
    couleurs: dict[str, str] = Field(default_factory=dict)
    titres: list[str] = Field(default_factory=list)
    descriptions: list[str] = Field(default_factory=list)
    temoignages: list[str] = Field(default_factory=list)
    markdown: str | None = None
    raw_json: dict[str, Any] | None = None


def _first_str(value: Any) -> str | None:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    if isinstance(value, list):
        for item in value:
            found = _first_str(item)
            if found:
                return found
    return None


def _normalize_url(url: str) -> str:
    cleaned = url.strip()
    if not cleaned:
        raise FirecrawlError("URL vide.")
    parsed = urlparse(cleaned)
    if parsed.scheme not in ("http", "https"):
        raise FirecrawlError("URL invalide (http/https requis).")
    return cleaned


def _absolutize_url(base_url: str, href: str) -> str | None:
    href = href.strip()
    if not href or href.startswith("data:"):
        return None
    return urljoin(base_url, href)


def _extract_images_from_html(html: str, base_url: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for match in _IMG_SRC_RE.finditer(html):
        absolute = _absolutize_url(base_url, match.group(1))
        if absolute and absolute not in seen:
            seen.add(absolute)
            urls.append(absolute)
    return urls


def _extract_images_from_markdown(markdown: str, base_url: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for match in _MD_IMG_RE.finditer(markdown):
        absolute = _absolutize_url(base_url, match.group(1))
        if absolute and absolute not in seen:
            seen.add(absolute)
            urls.append(absolute)
    return urls


def _extract_cta_from_html(html: str) -> list[str]:
    texts: list[str] = []
    seen: set[str] = set()
    for match in _CTA_RE.finditer(html):
        text = " ".join(match.group(1).split())
        low = text.lower()
        if len(text) < 2 or len(text) > 120:
            continue
        if low in seen:
            continue
        if any(skip in low for skip in ("cookie", "menu", "linkedin", "facebook")):
            continue
        seen.add(low)
        texts.append(text)
    return texts[:24]


def _extract_couleurs(branding: dict[str, Any] | None, html: str) -> dict[str, str]:
    couleurs: dict[str, str] = {}
    if isinstance(branding, dict):
        colors = branding.get("colors")
        if isinstance(colors, dict):
            for key in ("primary", "secondary", "accent", "background", "textPrimary"):
                val = colors.get(key)
                if isinstance(val, str) and val.startswith("#"):
                    couleurs[key] = val
    if not couleurs and html:
        found = _HEX_COLOR_RE.findall(html[:80_000])
        uniq: list[str] = []
        for hex_color in found:
            if hex_color.lower() not in {c.lower() for c in uniq}:
                uniq.append(hex_color)
            if len(uniq) >= 5:
                break
        if uniq:
            couleurs["primary"] = uniq[0]
            if len(uniq) > 1:
                couleurs["secondary"] = uniq[1]
            if len(uniq) > 2:
                couleurs["accent"] = uniq[2]
    return couleurs


def _sections_from_markdown(markdown: str) -> list[ScrapeSection]:
    sections: list[ScrapeSection] = []
    current_type = "other"
    current_heading: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        nonlocal current_heading, buffer, current_type
        if current_heading or buffer:
            sections.append(
                ScrapeSection(
                    type=current_type,
                    heading=current_heading,
                    summary=" ".join(buffer)[:400] if buffer else None,
                    sample_texts=buffer[:3],
                )
            )
        buffer = []

    def guess_type(heading: str) -> str:
        low = heading.lower()
        if any(w in low for w in ("accueil", "welcome", "hero", "bienvenue")):
            return "hero"
        if any(w in low for w in ("about", "à propos", "propos", "qui sommes")):
            return "about"
        if any(w in low for w in ("service", "offre", "prestation", "solution")):
            return "services"
        if any(w in low for w in ("tarif", "pricing", "prix", "forfait")):
            return "pricing"
        if any(w in low for w in ("contact", "nous contacter", "rendez-vous")):
            return "contact"
        if any(w in low for w in ("témoign", "avis", "review", "client")):
            return "testimonials"
        if "faq" in low or "question" in low:
            return "faq"
        return "other"

    for line in (markdown or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            flush()
            current_heading = stripped.lstrip("#").strip()
            current_type = guess_type(current_heading)
            continue
        if stripped and len(stripped) > 20:
            buffer.append(stripped[:240])
    flush()
    return sections


def _merge_sections(
    llm_sections: list[dict[str, Any]] | None,
    markdown: str,
) -> list[ScrapeSection]:
    if llm_sections:
        out: list[ScrapeSection] = []
        for row in llm_sections:
            if not isinstance(row, dict):
                continue
            stype = str(row.get("type") or "other").strip().lower()
            if stype not in SECTION_ORDER:
                stype = "other"
            out.append(
                ScrapeSection(
                    type=stype,
                    heading=_first_str(row.get("heading")),
                    summary=_first_str(row.get("summary")),
                )
            )
        if out:
            return out
    return _sections_from_markdown(markdown)


def _parse_firecrawl_payload(url: str, payload: dict[str, Any]) -> ScrapeResult:
    if not payload.get("success"):
        raise FirecrawlError(str(payload.get("error") or "Échec Firecrawl."))

    data = payload.get("data")
    if not isinstance(data, dict):
        raise FirecrawlError("Réponse Firecrawl sans données.")

    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    title = _first_str(metadata.get("title"))
    meta_description = _first_str(metadata.get("description"))

    markdown = data.get("markdown") if isinstance(data.get("markdown"), str) else ""
    html = data.get("html") if isinstance(data.get("html"), str) else ""
    branding = data.get("branding") if isinstance(data.get("branding"), dict) else None

    extracted = data.get("json")
    if isinstance(extracted, str):
        import json

        try:
            extracted = json.loads(extracted)
        except json.JSONDecodeError:
            extracted = {}
    if not isinstance(extracted, dict):
        extracted = {}

    titres = [str(t).strip() for t in (extracted.get("titres") or []) if str(t).strip()]
    descriptions = [
        str(d).strip() for d in (extracted.get("descriptions") or []) if str(d).strip()
    ]
    cta_texts = [
        str(c).strip() for c in (extracted.get("cta_texts") or []) if str(c).strip()
    ]
    temoignages = [
        str(t).strip() for t in (extracted.get("temoignages") or []) if str(t).strip()
    ]

    if not cta_texts and html:
        cta_texts = _extract_cta_from_html(html)

    sections = _merge_sections(extracted.get("sections"), markdown)

    image_urls: list[str] = []
    raw_images = data.get("images")
    if isinstance(raw_images, list):
        for item in raw_images:
            if isinstance(item, str) and item.strip():
                image_urls.append(item.strip())
            elif isinstance(item, dict):
                src = item.get("url") or item.get("src")
                if isinstance(src, str) and src.strip():
                    image_urls.append(src.strip())
    if html:
        image_urls.extend(_extract_images_from_html(html, url))
    if markdown:
        image_urls.extend(_extract_images_from_markdown(markdown, url))

    seen_img: set[str] = set()
    images: list[ScrapeImage] = []
    for index, img_url in enumerate(image_urls):
        if img_url in seen_img:
            continue
        seen_img.add(img_url)
        role = "hero" if index == 0 else "content"
        images.append(ScrapeImage(url=img_url, role=role))

    couleurs = _extract_couleurs(branding, html)

    return ScrapeResult(
        url=url,
        title=title,
        meta_description=meta_description,
        sections=sections,
        images=images,
        cta_texts=cta_texts[:30],
        couleurs=couleurs,
        titres=titres[:20],
        descriptions=descriptions[:20],
        temoignages=temoignages[:12],
        markdown=markdown[:50_000] if markdown else None,
        raw_json=extracted or None,
    )


class FirecrawlClient:
    """Appels HTTP Firecrawl."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def api_key(self) -> str:
        return plain_secret_str(self._settings.firecrawl_api_key)

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _timeout(self) -> httpx.Timeout:
        seconds = float(self._settings.firecrawl_http_timeout_seconds or DEFAULT_TIMEOUT_SECONDS)
        return httpx.Timeout(seconds, connect=15.0)

    def _build_formats(self, include_images: bool) -> list[dict[str, Any]]:
        formats: list[dict[str, Any]] = [
            {"type": "markdown"},
            {"type": "html"},
            {"type": "branding"},
            {
                "type": "json",
                "schema": SCRAPE_JSON_SCHEMA,
                "prompt": SCRAPE_JSON_PROMPT,
            },
        ]
        if include_images:
            formats.insert(2, {"type": "images"})
        return formats

    async def scrape(self, url: str, *, include_images: bool = True) -> ScrapeResult:
        if not self.is_configured():
            raise FirecrawlError("FIRECRAWL_API_KEY non configurée.")

        clean_url = _normalize_url(url)
        body = {
            "url": clean_url,
            "onlyMainContent": True,
            "formats": self._build_formats(include_images),
            "timeout": int(self._timeout().read * 1000),
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self._timeout()) as client:
            response = await client.post(
                f"{FIRECRAWL_API_BASE}/scrape",
                json=body,
                headers=headers,
            )

        if response.status_code >= 400:
            snippet = response.text[:400]
            raise FirecrawlError(f"Firecrawl HTTP {response.status_code}: {snippet}")

        return _parse_firecrawl_payload(clean_url, response.json())


async def firecrawl_scrape(
    url: str,
    *,
    include_images: bool = True,
    settings: Settings | None = None,
) -> ScrapeResult:
    return await FirecrawlClient(settings).scrape(url, include_images=include_images)

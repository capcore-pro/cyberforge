"""
ContentAI — Agent 3.

Remplit les placeholders du template HTML avec le contenu client réel
(research, secteur, design system). Pas de LLM — déterministe et vérifiable.
"""

from __future__ import annotations

import html as html_lib
import logging
import re
from typing import Any

from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from agents.design_system_ai import DesignSystemJSON, design_system_to_css_variables
from agents.template_ai import fill_template_placeholders
from core.agent_contract import AgentContractError, AgentResult
from agents.content_slots import (
    build_app_slots,
    build_default_contact_slots,
    build_desktop_slots,
    build_ecommerce_slots,
    build_reservation_slots,
    ensure_contact_slots,
)
from tools.html_markdown import strip_markdown_code_fences
from tools.client_content_profile import (
    build_client_content_profile,
    humanize_sector_label,
    resolve_client_business_name,
    sanitize_city,
)

logger = logging.getLogger(__name__)

_AGENT_ID = "content_ai"
_AGENT_NAME = "ContentAI"

_PLACEHOLDER_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")

_FORBIDDEN_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\blorem\s+ipsum\b", re.I), "lorem_ipsum"),
    (re.compile(r"\bService\s+[123]\b", re.I), "generic_service"),
    (re.compile(r"\bVotre\s+texte\b", re.I), "placeholder_text"),
    (re.compile(r"\bLorem\b", re.I), "lorem"),
    (re.compile(r'(?<![\w-])placeholder(?!\s*=)', re.I), "placeholder_word"),
    (re.compile(r">\s*Texte\s+générique\s*<", re.I), "generic_text"),
)

# Prestations réelles par template sectoriel
_TEMPLATE_SERVICES: dict[str, list[str]] = {
    "vitrine_alimentaire": [
        "Pains et viennoiseries au levain",
        "Pâtisseries maison et desserts",
        "Traiteur & commandes événements",
    ],
    "vitrine_artisan": [
        "Dépannage et réparations urgentes",
        "Installation et rénovation",
        "Devis gratuit sous 48 h",
        "Maintenance et entretien",
    ],
    "vitrine_sante": [
        "Consultations et bilans de santé",
        "Soins personnalisés et suivi",
        "Prise en charge sur rendez-vous",
    ],
    "vitrine_beaute": [
        "Coupe & coiffure tendance",
        "Soins visage et bien-être",
        "Manucure & nail art",
    ],
    "vitrine_nautisme": [
        "Cours et stages de voile",
        "Location de bateaux",
        "Entretien & services nautiques",
    ],
    "vitrine_default": [
        "Accompagnement sur mesure",
        "Conseil et expertise métier",
        "Suivi client réactif",
    ],
}

_HERO_TITLE_BUILDERS: dict[str, str] = {
    "vitrine_alimentaire": "{brand} — l'artisan {sector} de {city}",
    "vitrine_artisan": "{brand} : votre expert {sector} à {city}",
    "vitrine_sante": "{brand} — {sector} de confiance à {city}",
    "vitrine_beaute": "{brand} — {sector} & bien-être à {city}",
    "vitrine_nautisme": "{brand} — {sector} sur la côte de {city}",
    "vitrine_default": "{brand} — {sector} professionnel à {city}",
}


class ContentFillResult(BaseModel):
    html: str = Field(min_length=500)
    client_name: str
    sector: str
    city: str
    placeholders_filled: list[str] = Field(default_factory=list)
    keywords_used: list[str] = Field(default_factory=list)


def _coerce_research_dict(research_content: Any | None) -> dict[str, Any]:
    if research_content is None:
        return {}
    if hasattr(research_content, "model_dump"):
        return research_content.model_dump()
    if isinstance(research_content, dict):
        return research_content
    return {}


def _research_keywords(research: dict[str, Any], limit: int = 8) -> list[str]:
    raw = research.get("mots_cles") or research.get("keywords") or []
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        text = str(item).strip()
        if not text or len(text) < 2:
            continue
        if re.match(r"^service\s*\d+$", text, re.I):
            continue
        if text not in out:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def _resolve_services(
    template_id: str,
    research_keywords: list[str],
    sector_label: str,
) -> tuple[str, str, str]:
    """Trois libellés de services sectoriels — jamais « Service N »."""
    catalog = list(_TEMPLATE_SERVICES.get(template_id, _TEMPLATE_SERVICES["vitrine_default"]))
    if len(catalog) > 4:
        catalog = catalog[:4]

    merged: list[str] = []
    for kw in research_keywords:
        cleaned = kw.strip().capitalize()
        if cleaned and cleaned not in merged and not re.match(r"^service\s*\d", cleaned, re.I):
            merged.append(cleaned)
    for item in catalog:
        if item not in merged:
            merged.append(item)
    while len(merged) < 3:
        merged.append(f"Expertise {sector_label} {len(merged) + 1}")

    return merged[0], merged[1], merged[2]


def _build_hero_title(
    brand: str,
    sector_label: str,
    city: str,
    template_id: str,
    research: dict[str, Any],
) -> str:
    """Titre accrocheur mentionnant secteur et/ou ville."""
    city_part = city if city and city.lower() != "votre ville" else ""
    sector_part = sector_label or "activité locale"
    pattern = _HERO_TITLE_BUILDERS.get(
        template_id,
        _HERO_TITLE_BUILDERS["vitrine_default"],
    )
    title = pattern.format(
        brand=brand,
        sector=sector_part.lower(),
        city=city_part or "votre région",
    )
    if research.get("contenu_suggere") and isinstance(research["contenu_suggere"], list):
        first = str(research["contenu_suggere"][0]).strip()
        if first and len(first) < 80 and not _looks_generic(first):
            title = f"{brand} — {first}"[:90]
    return title[:90]


def _build_hero_subtitle(
    brand: str,
    sector_label: str,
    city: str,
    keywords: list[str],
    research: dict[str, Any],
) -> str:
    kw_part = ""
    if keywords:
        kw_part = f" Spécialités : {', '.join(keywords[:3])}."
    city_part = f" À {city}." if city and city.lower() != "votre ville" else ""
    base = (
        f"{brand} vous accueille pour une expérience {sector_label.lower()} "
        f"d'excellence.{city_part}{kw_part}"
    )
    tendances = research.get("tendances")
    if isinstance(tendances, list) and tendances:
        t0 = str(tendances[0]).strip()
        if t0 and len(t0) < 120:
            base = f"{t0} — {brand}{city_part}."
    return base[:220]


def _looks_generic(text: str) -> bool:
    lower = text.lower()
    return any(
        x in lower
        for x in ("lorem", "service 1", "votre texte", "placeholder", "example")
    )


def _design_system_slots(design_system: Any | None) -> dict[str, str]:
    if design_system is None:
        return {}
    if isinstance(design_system, DesignSystemJSON):
        doc = design_system
    elif isinstance(design_system, dict):
        try:
            doc = DesignSystemJSON.model_validate(design_system)
        except Exception:
            colors = design_system.get("colors") or {}
            fonts = design_system.get("fonts") or {}
            return {
                "PRIMARY_COLOR": str(colors.get("primary", "#1C2833")),
                "SECONDARY_COLOR": str(colors.get("secondary", "#FFFFFF")),
                "FONT_HEADING": str(fonts.get("heading", "Inter")),
                "FONT_BODY": str(fonts.get("body", "Inter")),
                "GOOGLE_FONTS_URL": str(design_system.get("google_fonts_url", "")),
            }
    else:
        return {}
    return {
        "PRIMARY_COLOR": doc.colors.primary,
        "SECONDARY_COLOR": doc.colors.secondary,
        "FONT_HEADING": doc.fonts.heading,
        "FONT_BODY": doc.fonts.body,
        "GOOGLE_FONTS_URL": doc.google_fonts_url,
    }


def build_content_slots(
    *,
    client_name: str,
    sector: str,
    city: str,
    template_html: str,
    research_content: Any | None = None,
    design_system: Any | None = None,
    user_prompt: str = "",
    template_id: str = "vitrine_default",
) -> dict[str, str]:
    """Construit toutes les valeurs de placeholders pour ContentAI."""
    research = _coerce_research_dict(research_content)
    ds = _design_system_slots(design_system)
    profile = build_client_content_profile(
        user_prompt=user_prompt,
        research_brief=research_content,
    )
    city_clean = sanitize_city(city or research.get("ville") or profile.city) or "votre ville"
    sector_raw = sector or research.get("secteur") or profile.sector
    brand = resolve_client_business_name(
        client_name or profile.company_name or "",
        sector=str(sector_raw or ""),
        city=city_clean if city_clean != "votre ville" else profile.city,
        user_prompt=user_prompt,
    )
    sector_label = humanize_sector_label(
        sector or research.get("secteur") or profile.sector,
        profile.keywords,
        user_prompt=user_prompt,
    )

    tid = (template_id or "vitrine_default").strip()
    if tid.startswith("ecommerce_"):
        return build_ecommerce_slots(
            tid,
            brand,
            city_clean,
            ds,
            research,
            user_prompt=user_prompt,
        )
    if tid.startswith("reservation_"):
        return build_reservation_slots(
            tid,
            brand,
            city_clean,
            ds,
            user_prompt=user_prompt,
            research=research,
        )
    if tid.startswith("app_"):
        slots = build_app_slots(tid, brand, ds, sector_label)
        return ensure_contact_slots(
            slots,
            brand,
            city_clean,
            user_prompt=user_prompt,
            research=research,
        )
    if tid.startswith("desktop_"):
        slots = build_desktop_slots(tid, brand, ds)
        return ensure_contact_slots(
            slots,
            brand,
            city_clean,
            user_prompt=user_prompt,
            research=research,
        )

    keywords = _research_keywords(research)
    if not keywords:
        keywords = list(profile.keywords[:5])

    svc1, svc2, svc3 = _resolve_services(template_id, keywords, sector_label)

    hero_title = _build_hero_title(brand, sector_label, city_clean, template_id, research)
    hero_subtitle = _build_hero_subtitle(
        brand, sector_label, city_clean, keywords, research
    )

    contact = build_default_contact_slots(
        brand,
        city_clean,
        user_prompt=user_prompt,
        research=research,
    )

    slots: dict[str, str] = {
        "CLIENT_NAME": html_lib.escape(brand),
        "SECTOR": html_lib.escape(sector_label),
        "CITY": html_lib.escape(city_clean),
        "PRIMARY_COLOR": ds.get("PRIMARY_COLOR", "#1C2833"),
        "SECONDARY_COLOR": ds.get("SECONDARY_COLOR", "#FFFFFF"),
        "FONT_HEADING": ds.get("FONT_HEADING", "Inter"),
        "FONT_BODY": ds.get("FONT_BODY", "Inter"),
        "HERO_TITLE": html_lib.escape(hero_title),
        "HERO_SUBTITLE": html_lib.escape(hero_subtitle),
        "SERVICE_1": html_lib.escape(svc1),
        "SERVICE_2": html_lib.escape(svc2),
        "SERVICE_3": html_lib.escape(svc3),
        "CTA_TEXT": html_lib.escape(f"Contactez {brand}"),
        **contact,
        "GOOGLE_FONTS_URL": ds.get(
            "GOOGLE_FONTS_URL",
            "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap",
        ),
    }
    return slots


def _apply_design_system_css(html: str, design_system: Any | None) -> str:
    """Injecte / renforce les variables CSS de la loi visuelle."""
    if not design_system:
        return html
    try:
        if isinstance(design_system, dict):
            doc = DesignSystemJSON.model_validate(design_system)
        elif isinstance(design_system, DesignSystemJSON):
            doc = design_system
        else:
            return html
    except Exception:
        return html

    css_block = design_system_to_css_variables(doc)
    link = f'<link rel="stylesheet" href="{doc.google_fonts_url}" />\n'
    style = f'<style id="cf-design-system">{css_block}</style>\n'
    snippet = link + style

    if "cf-design-system" in html:
        html = re.sub(
            r'<style id="cf-design-system">[\s\S]*?</style>',
            style.strip(),
            html,
            count=1,
        )
    elif "</head>" in html.lower():
        html = re.sub(r"</head>", f"  {snippet}</head>", html, count=1, flags=re.I)
    else:
        html = snippet + html
    return html


def _fix_action_links(html: str) -> str:
    """Remplace href='#' inertes par des ancres ou actions réelles."""
    html = re.sub(
        r'<a([^>]*)\shref=["\']#["\']([^>]*)>',
        r'<a\1 href="#contact"\2>',
        html,
        flags=re.I,
    )
    html = re.sub(
        r'<form([^>]*)action=["\']#["\']([^>]*)>',
        r'<form\1 action="javascript:void(0)"\2>',
        html,
        flags=re.I,
    )
    # Liens logo → accueil
    html = re.sub(
        r'(<a[^>]*class=["\'][^"\']*logo[^"\']*["\'][^>]*)href=["\']#contact["\']',
        r'\1 href="#top"',
        html,
        count=1,
        flags=re.I,
    )
    if 'id="top"' not in html and "<body" in html.lower():
        html = re.sub(r"<body([^>]*)>", r'<body\1 id="top">', html, count=1, flags=re.I)
    return html


def _validate_content_html(html: str) -> None:
    remaining = sorted(set(_PLACEHOLDER_RE.findall(html)))
    if remaining:
        raise AgentContractError(
            agent_id=_AGENT_ID,
            code="unfilled_placeholders",
            message=f"Placeholders restants : {', '.join(remaining)}",
        )
    for pattern, code in _FORBIDDEN_PATTERNS:
        if pattern.search(html):
            raise AgentContractError(
                agent_id=_AGENT_ID,
                code=f"forbidden_{code}",
                message=f"Contenu interdit détecté ({code}).",
            )
    if len(html.strip()) < 500:
        raise AgentContractError(
            agent_id=_AGENT_ID,
            code="empty_html",
            message="HTML final trop court.",
        )


def fill_template_content(
    *,
    template_html: str,
    client_name: str,
    sector: str,
    city: str = "",
    research_content: Any | None = None,
    design_system: Any | None = None,
    user_prompt: str = "",
    template_id: str = "vitrine_default",
) -> AgentResult[ContentFillResult]:
    """
    Remplit le template et retourne le HTML final.
    Échoue explicitement si placeholder ou contenu interdit.
    """
    if not (template_html or "").strip():
        return AgentResult.failure(
            agent_id=_AGENT_ID,
            agent_name=_AGENT_NAME,
            code="missing_template",
            message="template_html obligatoire.",
        )
    profile = build_client_content_profile(
        user_prompt=user_prompt,
        research_brief=research_content,
    )
    research_dict = _coerce_research_dict(research_content)
    city_hint = city or research_dict.get("ville") or profile.city or ""
    resolved_name = resolve_client_business_name(
        client_name or profile.company_name or "",
        sector=sector or profile.sector or "",
        city=city_hint,
        user_prompt=user_prompt,
    )
    if len(resolved_name.strip()) < 2:
        return AgentResult.failure(
            agent_id=_AGENT_ID,
            agent_name=_AGENT_NAME,
            code="missing_client_name",
            message="client_name obligatoire pour ContentAI.",
        )

    try:
        slots = build_content_slots(
            client_name=resolved_name,
            sector=sector,
            city=city,
            template_html=template_html,
            research_content=research_content,
            design_system=design_system,
            user_prompt=user_prompt,
            template_id=template_id,
        )
        html, filled, missing = fill_template_placeholders(template_html, slots)
        if missing:
            return AgentResult.failure(
                agent_id=_AGENT_ID,
                agent_name=_AGENT_NAME,
                code="missing_placeholders",
                message=f"Placeholders non remplis : {', '.join(missing)}",
            )
        html = strip_markdown_code_fences(html)
        html = _apply_design_system_css(html, design_system)
        html = _fix_action_links(html)
        _validate_content_html(html)

        brand = slots.get("CLIENT_NAME", html_lib.escape(resolved_name))
        sector_out = slots.get("SECTOR") or html_lib.escape(
            humanize_sector_label(sector or profile.sector, profile.keywords, user_prompt=user_prompt)
        )
        city_out = slots.get("CITY") or html_lib.escape(city_hint or "votre ville")
        keywords_used = [
            html_lib.unescape(slots[k])
            for k in ("SERVICE_1", "SERVICE_2", "SERVICE_3", "PRODUCT_1_NAME", "CATEGORY_1")
            if k in slots
        ][:3]
        result = ContentFillResult(
            html=html,
            client_name=html_lib.unescape(brand) if "&" in brand else brand,
            sector=html_lib.unescape(sector_out) if "&" in sector_out else sector_out,
            city=html_lib.unescape(city_out) if "&" in city_out else city_out,
            placeholders_filled=filled,
            keywords_used=keywords_used,
        )
    except AgentContractError as exc:
        return AgentResult.failure(
            agent_id=_AGENT_ID,
            agent_name=_AGENT_NAME,
            code=exc.code,
            message=exc.message,
            detail=exc.detail,
        )
    except Exception as exc:
        logger.exception("[ContentAI] échec remplissage")
        return AgentResult.failure(
            agent_id=_AGENT_ID,
            agent_name=_AGENT_NAME,
            code="content_fill_failed",
            message="Impossible de produire le HTML de contenu.",
            detail=str(exc),
        )

    logger.info(
        "[ContentAI] OK | client=%s | template=%s | services=%s",
        result.client_name,
        template_id,
        result.keywords_used,
    )
    return AgentResult.success(
        agent_id=_AGENT_ID,
        agent_name=_AGENT_NAME,
        data=result,
        meta={"template_id": template_id},
    )


class ContentAgent(BaseAgent):
    @property
    def agent_id(self) -> str:
        return _AGENT_ID

    @property
    def name(self) -> str:
        return _AGENT_NAME

    async def run(self, prompt: str, **kwargs: Any) -> str:
        result = fill_template_content(
            template_html=kwargs.get("template_html") or "",
            client_name=kwargs.get("client_name") or "",
            sector=kwargs.get("sector") or "",
            city=kwargs.get("city") or "",
            research_content=kwargs.get("research_content"),
            design_system=kwargs.get("design_system"),
            user_prompt=prompt,
            template_id=kwargs.get("template_id") or "vitrine_default",
        )
        if not result.ok or result.data is None:
            err = result.error
            raise AgentContractError(
                agent_id=_AGENT_ID,
                code=err.code if err else "failure",
                message=err.message if err else "Échec ContentAI",
                detail=err.detail if err else None,
            )
        return result.data.html

    async def fill(
        self,
        *,
        template_html: str,
        client_name: str,
        sector: str,
        city: str = "",
        research_content: Any | None = None,
        design_system: Any | None = None,
        user_prompt: str = "",
        template_id: str = "vitrine_default",
    ) -> AgentResult[ContentFillResult]:
        return fill_template_content(
            template_html=template_html,
            client_name=client_name,
            sector=sector,
            city=city,
            research_content=research_content,
            design_system=design_system,
            user_prompt=user_prompt,
            template_id=template_id,
        )

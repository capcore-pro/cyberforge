"""
TemplateAI — Agent 2.

Sélectionne et charge le template HTML sectoriel de base, puis remplit les placeholders.
Une seule responsabilité : livrer un HTML complet prêt pour les agents suivants.
"""

from __future__ import annotations

import html as html_lib
import logging
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from agents.coremind_agent import ProjectType
from agents.design_system_ai import (
    DesignSystemJSON,
    resolve_visual_family,
)
from core.agent_contract import AgentContractError, AgentResult
from tools.client_content_profile import (
    build_client_content_profile,
    format_client_h1,
    format_client_page_title,
    format_client_tagline,
    humanize_sector_label,
    sanitize_brand_name,
)
from tools.toolbox_sectors import detect_sector_from_prompt, normalize_sector_key

logger = logging.getLogger(__name__)

_AGENT_ID = "template_ai"
_AGENT_NAME = "TemplateAI"

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "sectors"

# Famille visuelle / secteur → fichier template
_SECTOR_TEMPLATE_FILES: dict[str, str] = {
    "alimentaire": "vitrine_alimentaire.html",
    "restauration": "vitrine_alimentaire.html",
    "marin_sport": "vitrine_nautisme.html",
    "artisan_batiment": "vitrine_artisan.html",
    "sante_bien_etre": "vitrine_sante.html",
    "beaute_mode": "vitrine_beaute.html",
    "tech_digital": "vitrine_default.html",
    "juridique_finance": "vitrine_default.html",
    "nautisme": "vitrine_nautisme.html",
    "sport": "vitrine_nautisme.html",
    "artisan_batiment": "vitrine_artisan.html",
    "artisanat": "vitrine_artisan.html",
    "sante_bien_etre": "vitrine_sante.html",
    "sante": "vitrine_sante.html",
    "beaute_mode": "vitrine_beaute.html",
    "beaute": "vitrine_beaute.html",
    "tech_digital": "vitrine_default.html",
    "juridique_finance": "vitrine_default.html",
    "commerce": "vitrine_default.html",
    "immobilier": "vitrine_default.html",
    "technologie": "vitrine_default.html",
    "education": "vitrine_sante.html",
}

_DEFAULT_TEMPLATE = "vitrine_default.html"

# Désambiguïsation prompt → fichier (prioritaire sur « cabinet » juridique, etc.)
_PROMPT_TEMPLATE_HINTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("dentaire", "dentiste", "kiné", "kine", "ostéo", "osteo", "psychologue", "clinique médicale"), "vitrine_sante.html"),
    (("avocat", "notaire", "juridique", "finance", "comptable"), "vitrine_default.html"),
    (("voilerie", "école de voile", "ecole de voile", "chantier naval", "location bateau"), "vitrine_nautisme.html"),
)

_PLACEHOLDER_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


class SectorTemplateResult(BaseModel):
    """Résultat TemplateAI — HTML sectoriel rempli."""

    template_id: str
    template_file: str
    sector: str
    visual_family: str
    html: str = Field(min_length=100)
    placeholders_filled: list[str] = Field(default_factory=list)
    missing_placeholders: list[str] = Field(default_factory=list)


def list_sector_templates() -> dict[str, str]:
    """Catalogue template_id → nom de fichier."""
    return dict(_SECTOR_TEMPLATE_FILES)


def resolve_sector_template_file(
    sector: str,
    user_prompt: str = "",
) -> tuple[str, str]:
    """
    Retourne (template_id, filename) selon le secteur détecté.
    template_id = nom sans extension.
    """
    sector_key = normalize_sector_key(sector or "")
    blob = f"{sector_key} {user_prompt}".lower()
    filename: str | None = None
    for keywords, hinted_file in _PROMPT_TEMPLATE_HINTS:
        if any(kw in blob for kw in keywords):
            filename = hinted_file
            break
    family = resolve_visual_family(sector_key, user_prompt)
    if not filename:
        filename = (
            _SECTOR_TEMPLATE_FILES.get(family)
            or _SECTOR_TEMPLATE_FILES.get(sector_key)
            or _DEFAULT_TEMPLATE
        )
    template_id = Path(filename).stem
    return template_id, filename


def load_sector_template_html(filename: str) -> str:
    """Charge le fichier HTML brut depuis backend/templates/sectors/."""
    path = _TEMPLATES_DIR / filename
    if not path.is_file():
        raise AgentContractError(
            agent_id=_AGENT_ID,
            code="template_not_found",
            message=f"Template sectoriel introuvable : {filename}",
            detail=str(path),
        )
    return path.read_text(encoding="utf-8")


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
                "PRIMARY_COLOR": str(colors.get("primary", "#2563EB")),
                "SECONDARY_COLOR": str(colors.get("secondary", "#FFFFFF")),
                "ACCENT_COLOR": str(colors.get("accent", "#D97706")),
                "FONT_HEADING": str(fonts.get("heading", "Inter")),
                "FONT_BODY": str(fonts.get("body", "Inter")),
                "GOOGLE_FONTS_URL": str(
                    design_system.get("google_fonts_url", "")
                ),
            }
    else:
        return {}

    return {
        "PRIMARY_COLOR": doc.colors.primary,
        "SECONDARY_COLOR": doc.colors.secondary,
        "ACCENT_COLOR": doc.colors.accent,
        "FONT_HEADING": doc.fonts.heading,
        "FONT_BODY": doc.fonts.body,
        "GOOGLE_FONTS_URL": doc.google_fonts_url,
    }


def build_template_slots(
    *,
    sector: str,
    user_prompt: str,
    research_brief: Any | None = None,
    design_system: Any | None = None,
    plan: Any | None = None,
) -> dict[str, str]:
    """Construit toutes les valeurs de placeholders."""
    profile = build_client_content_profile(
        user_prompt=user_prompt,
        research_brief=research_brief,
        plan=plan,
    )
    brand = sanitize_brand_name(
        profile.company_name or profile.display_name,
        user_prompt=user_prompt,
    )
    sector_label = humanize_sector_label(
        profile.sector or sector,
        profile.keywords,
        user_prompt=user_prompt,
    )
    city = html_lib.escape((profile.city or "").strip() or "votre ville")
    keywords = profile.keywords[:3]
    while len(keywords) < 3:
        keywords.append(f"Service {len(keywords) + 1}")

    ds = _design_system_slots(design_system)
    primary = ds.get("PRIMARY_COLOR", "#5C3A21")
    secondary = ds.get("SECONDARY_COLOR", "#FCF7F0")

    hero_title = format_client_h1(profile, user_prompt=user_prompt)
    hero_subtitle = format_client_tagline(profile, user_prompt=user_prompt)
    page_title = format_client_page_title(profile, user_prompt=user_prompt)

    slots: dict[str, str] = {
        "CLIENT_NAME": html_lib.escape(brand),
        "SECTOR": html_lib.escape(sector_label),
        "CITY": city,
        "PRIMARY_COLOR": primary,
        "SECONDARY_COLOR": secondary,
        "ACCENT_COLOR": ds.get("ACCENT_COLOR", primary),
        "FONT_HEADING": ds.get("FONT_HEADING", "Playfair Display"),
        "FONT_BODY": ds.get("FONT_BODY", "Lato"),
        "HERO_TITLE": html_lib.escape(hero_title),
        "HERO_SUBTITLE": html_lib.escape(hero_subtitle),
        "PAGE_TITLE": html_lib.escape(page_title),
        "SERVICE_1": html_lib.escape(keywords[0]),
        "SERVICE_2": html_lib.escape(keywords[1]),
        "SERVICE_3": html_lib.escape(keywords[2]),
        "CTA_TEXT": html_lib.escape(f"Contactez {brand}"),
        "PHONE": html_lib.escape("01 23 45 67 89"),
        "EMAIL": html_lib.escape(f"contact@{_email_slug(brand)}.fr"),
        "ADDRESS": html_lib.escape(f"12 rue principale, {city}"),
        "GOOGLE_FONTS_URL": ds.get(
            "GOOGLE_FONTS_URL",
            "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap",
        ),
    }
    return slots


def _email_slug(brand: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "", brand.lower())
    return slug[:24] or "entreprise"


def fill_template_placeholders(html: str, slots: dict[str, str]) -> tuple[str, list[str], list[str]]:
    """Remplace {{KEY}} ; signale les placeholders restants."""
    missing_before = set(_PLACEHOLDER_RE.findall(html))
    out = html
    filled: list[str] = []
    for key in sorted(missing_before):
        token = f"{{{{{key}}}}}"
        if key in slots:
            out = out.replace(token, slots[key])
            filled.append(key)
    remaining = sorted(set(_PLACEHOLDER_RE.findall(out)))
    return out, filled, remaining


def load_sector_template_raw(
    *,
    sector: str,
    user_prompt: str = "",
    plan: Any | None = None,
) -> AgentResult[SectorTemplateResult]:
    """Charge le template sectoriel SANS remplir les placeholders (ContentAI)."""
    sector_key = normalize_sector_key(sector or "") or detect_sector_from_prompt(
        user_prompt,
        project_type=getattr(plan, "project_type", None) if plan else None,
    )
    family = resolve_visual_family(sector_key, user_prompt)
    try:
        template_id, filename = resolve_sector_template_file(sector_key, user_prompt)
        raw_html = load_sector_template_html(filename)
        placeholders = sorted(set(_PLACEHOLDER_RE.findall(raw_html)))
        result = SectorTemplateResult(
            template_id=template_id,
            template_file=filename,
            sector=sector_key,
            visual_family=family,
            html=raw_html,
            placeholders_filled=[],
            missing_placeholders=placeholders,
        )
    except AgentContractError as exc:
        return AgentResult.failure(
            agent_id=_AGENT_ID,
            agent_name=_AGENT_NAME,
            code=exc.code,
            message=exc.message,
            detail=exc.detail,
        )
    return AgentResult.success(
        agent_id=_AGENT_ID,
        agent_name=_AGENT_NAME,
        data=result,
        meta={"template_id": template_id, "visual_family": family},
    )


def render_sector_template(
    *,
    sector: str,
    user_prompt: str = "",
    research_brief: Any | None = None,
    design_system: Any | None = None,
    plan: Any | None = None,
) -> AgentResult[SectorTemplateResult]:
    """Charge le template sectoriel et remplit les placeholders (legacy / tests)."""
    sector_key = normalize_sector_key(sector or "") or detect_sector_from_prompt(
        user_prompt,
        project_type=getattr(plan, "project_type", None) if plan else None,
    )
    family = resolve_visual_family(sector_key, user_prompt)

    try:
        template_id, filename = resolve_sector_template_file(sector_key, user_prompt)
        raw_html = load_sector_template_html(filename)
        slots = build_template_slots(
            sector=sector_key,
            user_prompt=user_prompt,
            research_brief=research_brief,
            design_system=design_system,
            plan=plan,
        )
        html, filled, missing = fill_template_placeholders(raw_html, slots)

        if missing:
            return AgentResult.failure(
                agent_id=_AGENT_ID,
                agent_name=_AGENT_NAME,
                code="missing_placeholders",
                message=f"Placeholders non remplis : {', '.join(missing)}",
                detail="Vérifiez le template HTML sectoriel.",
            )

        if len(html.strip()) < 500:
            return AgentResult.failure(
                agent_id=_AGENT_ID,
                agent_name=_AGENT_NAME,
                code="empty_template",
                message="Le HTML sectoriel rendu est trop court.",
            )

        result = SectorTemplateResult(
            template_id=template_id,
            template_file=filename,
            sector=sector_key,
            visual_family=family,
            html=html,
            placeholders_filled=filled,
            missing_placeholders=missing,
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
        logger.exception("[TemplateAI] échec rendu template sectoriel")
        return AgentResult.failure(
            agent_id=_AGENT_ID,
            agent_name=_AGENT_NAME,
            code="template_render_failed",
            message="Impossible de charger ou remplir le template sectoriel.",
            detail=str(exc),
        )

    logger.info(
        "[TemplateAI] OK | template=%s | sector=%s | family=%s",
        template_id,
        sector_key,
        family,
    )
    return AgentResult.success(
        agent_id=_AGENT_ID,
        agent_name=_AGENT_NAME,
        data=result,
        meta={"template_id": template_id, "visual_family": family},
    )


class TemplateAgent(BaseAgent):
    @property
    def agent_id(self) -> str:
        return _AGENT_ID

    @property
    def name(self) -> str:
        return _AGENT_NAME

    async def run(self, prompt: str, **kwargs: Any) -> str:
        result = render_sector_template(
            sector=kwargs.get("sector") or "",
            user_prompt=prompt,
            research_brief=kwargs.get("research_brief"),
            design_system=kwargs.get("design_system"),
            plan=kwargs.get("plan"),
        )
        if not result.ok or result.data is None:
            err = result.error
            raise AgentContractError(
                agent_id=_AGENT_ID,
                code=err.code if err else "failure",
                message=err.message if err else "Échec TemplateAI",
                detail=err.detail if err else None,
            )
        return result.data.html

    async def load(
        self,
        *,
        sector: str,
        user_prompt: str = "",
        research_brief: Any | None = None,
        design_system: Any | None = None,
        plan: Any | None = None,
    ) -> AgentResult[SectorTemplateResult]:
        return render_sector_template(
            sector=sector,
            user_prompt=user_prompt,
            research_brief=research_brief,
            design_system=design_system,
            plan=plan,
        )

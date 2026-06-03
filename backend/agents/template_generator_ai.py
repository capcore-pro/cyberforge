"""
TemplateGeneratorAI — génère un template HTML sectoriel complet via Claude Sonnet.

Entrée : project_description, project_type, sector, design_system
Sortie : { html, template_id, summary }
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import httpx
from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from agents.design_system_ai import DesignSystemJSON
from config import get_settings
from security.llm_secrets import get_effective_llm_key
from tools.html_markdown import strip_markdown_code_fences

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

logger = logging.getLogger(__name__)

_AGENT_ID = "template_generator_ai"
_AGENT_NAME = "TemplateGeneratorAI"

MODEL = os.getenv("COREMIND_SONNET_MODEL", "claude-sonnet-4-5")
MAX_TOKENS = 16_000
TIMEOUT_SECONDS = 180.0

_PLACEHOLDER_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")

SYSTEM_PROMPT = """Tu es un expert front-end senior spécialisé dans les sites web premium pour PME françaises.
Tu génères UN SEUL fichier HTML5 complet, autonome, prêt pour injection de contenu CyberForge.

STRUCTURE OBLIGATOIRE :
- <!DOCTYPE html>, <html lang="fr">, <head> complet, <body>
- Header fixe ou sticky avec navigation (logo + ancres vers sections)
- Hero plein écran (min-height ~90vh) avec image de fond via {{HERO_IMAGE}} en CSS background ou <img>
- 3 à 5 sections <section> adaptées au secteur et au type de projet (services, à propos, galerie, contact, etc.)
- Footer avec coordonnées et mentions

PLACEHOLDERS OBLIGATOIRES (orthographe exacte, doubles accolades) :
- {{CLIENT_NAME}}, {{CLIENT_TAGLINE}} dans le hero et le header
- {{HERO_IMAGE}} pour l'image hero (attribut src ou url() dans CSS)
- Pour chaque section numérotée 1 à 5 utilisée : {{SECTION_N_TITLE}} et {{SECTION_N_CONTENT}}
  (ex. section 1 : {{SECTION_1_TITLE}} et {{SECTION_1_CONTENT}})

DESIGN SYSTEM (dans :root du <style> interne) :
- --color-primary et --color-secondary : reprendre EXACTEMENT les valeurs fournies
- Tu peux aussi définir --color-accent, --font-heading, --font-body si utile
- Lien <link rel="stylesheet" href="{{GOOGLE_FONTS_URL}}" /> ou URL Google Fonts fournie

IMAGES :
- Toute balise <img> destinée à VisionUI doit avoir class="cf-image"
- alt descriptif sur chaque image

CSS & UX :
- CSS dans <style> dans <head> (pas de fichier externe sauf Google Fonts)
- Mobile first, media queries pour tablette/desktop
- Contraste lisible, boutons CTA visibles
- Pas de JavaScript obligatoire (optionnel léger pour menu mobile)

INTERDIT :
- Markdown, explication hors HTML, commentaire « voici le code »
- Lorem ipsum, texte inventé à la place des placeholders
- Frameworks (React, Vue, Tailwind CDN)
- Contenu réel à la place des {{PLACEHOLDERS}}

Réponds UNIQUEMENT avec le document HTML complet, sans texte avant ou après."""

_anthropic_http = httpx.AsyncClient(timeout=TIMEOUT_SECONDS)
_anthropic = AsyncAnthropic(
    api_key=get_effective_llm_key("ANTHROPIC_API_KEY", get_settings()) or "",
    http_client=_anthropic_http,
)


class TemplateGeneratorResult(BaseModel):
    html: str = Field(min_length=200)
    template_id: str = Field(min_length=3)
    summary: str = ""


def _design_system_context(design_system: Any | None) -> dict[str, str]:
    if design_system is None:
        return {
            "primary": "#2563EB",
            "secondary": "#F8FAFC",
            "accent": "#D97706",
            "font_heading": "Inter",
            "font_body": "Inter",
            "google_fonts_url": (
                "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap"
            ),
        }
    if isinstance(design_system, DesignSystemJSON):
        doc = design_system
    elif isinstance(design_system, dict):
        try:
            doc = DesignSystemJSON.model_validate(design_system)
        except Exception:
            colors = design_system.get("colors") or {}
            fonts = design_system.get("fonts") or {}
            return {
                "primary": str(colors.get("primary", "#2563EB")),
                "secondary": str(colors.get("secondary", "#F8FAFC")),
                "accent": str(colors.get("accent", "#D97706")),
                "font_heading": str(fonts.get("heading", "Inter")),
                "font_body": str(fonts.get("body", "Inter")),
                "google_fonts_url": str(
                    design_system.get("google_fonts_url", "")
                )
                or "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap",
            }
    else:
        return _design_system_context(None)

    return {
        "primary": doc.colors.primary,
        "secondary": doc.colors.secondary,
        "accent": doc.colors.accent,
        "font_heading": doc.fonts.heading,
        "font_body": doc.fonts.body,
        "google_fonts_url": doc.google_fonts_url,
    }


def _project_type_label(project_type: str) -> str:
    key = (project_type or "").strip().lower()
    labels = {
        "vitrine_next": "site vitrine multi-pages",
        "ecommerce": "site e-commerce",
        "site_reservation": "site avec réservation en ligne",
        "site_web": "site vitrine",
        "landing_page": "landing page",
    }
    return labels.get(key, project_type or "site web")


def _template_id_prefix(project_type: str) -> str:
    key = (project_type or "").strip().lower()
    if key in ("ecommerce", "site_reservation", "vitrine_next"):
        return f"generated_{key}"
    return "generated_vitrine"


def _build_user_prompt(
    *,
    project_description: str,
    project_type: str,
    sector: str,
    design_system: Any | None,
) -> str:
    ds = _design_system_context(design_system)
    return (
        f"Type de projet : {_project_type_label(project_type)} ({project_type})\n"
        f"Secteur d'activité : {sector or 'activité locale'}\n\n"
        f"Description du projet :\n{project_description.strip()[:14000]}\n\n"
        f"Design system à respecter dans :root :\n"
        f"- --color-primary: {ds['primary']}\n"
        f"- --color-secondary: {ds['secondary']}\n"
        f"- --color-accent (optionnel): {ds['accent']}\n"
        f"- Polices : {ds['font_heading']} (titres), {ds['font_body']} (texte)\n"
        f"- {{GOOGLE_FONTS_URL}} : {ds['google_fonts_url']}\n\n"
        "Génère le HTML complet avec les placeholders listés dans les instructions système."
    )


def _extract_html_from_response(text: str) -> str:
    cleaned = strip_markdown_code_fences(text or "").strip()
    if not cleaned:
        return ""
    if re.search(r"<!DOCTYPE\s+html", cleaned, re.I) or re.search(
        r"<html\b", cleaned, re.I
    ):
        match = re.search(
            r"(<!DOCTYPE[\s\S]*</html>)",
            cleaned,
            flags=re.I,
        )
        if match:
            return match.group(1).strip()
        match = re.search(r"(<html[\s\S]*</html>)", cleaned, flags=re.I)
        if match:
            return match.group(1).strip()
    return cleaned


def _validate_generated_html(html: str) -> str | None:
    if len(html) < 800:
        return "HTML généré trop court"
    low = html.lower()
    if "<html" not in low or "</body>" not in low:
        return "structure HTML incomplète"
    if "{{client_name}}" not in low:
        return "placeholder {{CLIENT_NAME}} manquant"
    if "{{client_tagline}}" not in low:
        return "placeholder {{CLIENT_TAGLINE}} manquant"
    if "<img" in low and "cf-image" not in low:
        return "class cf-image manquante sur les images"
    if not re.search(r"<(header|nav)\b", html, re.I):
        return "header/nav manquant"
    if not re.search(
        r'(class=["\'][^"\']*hero|id=["\']hero|section[^>]+hero)',
        html,
        re.I,
    ):
        return "section hero manquante"
    if "{{section_1_title}}" not in low and "{{section_2_title}}" not in low:
        return "placeholders SECTION_N_TITLE manquants"
    return None


def _make_template_id(project_type: str, sector: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", (sector or "secteur").lower()).strip("_")[:20]
    prefix = _template_id_prefix(project_type)
    return f"{prefix}_{slug or 'custom'}"


async def run(
    *,
    project_description: str,
    project_type: str,
    sector: str,
    design_system: Any | None = None,
) -> TemplateGeneratorResult | None:
    """
    Génère un template HTML via Claude Sonnet.
    Retourne None en cas d'échec (le pipeline doit utiliser le catalogue sectoriel).
    """
    if os.environ.get("TEMPLATE_GENERATOR_AI", "1").strip().lower() in (
        "0",
        "false",
        "no",
        "off",
    ):
        logger.info("[TemplateGeneratorAI] désactivé (TEMPLATE_GENERATOR_AI=0)")
        return None

    api_key = get_effective_llm_key("ANTHROPIC_API_KEY", get_settings())
    if not api_key:
        logger.warning("[TemplateGeneratorAI] ANTHROPIC_API_KEY absente")
        return None

    user_message = _build_user_prompt(
        project_description=project_description,
        project_type=project_type,
        sector=sector,
        design_system=design_system,
    )

    try:
        response = await _anthropic.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
    except (TimeoutError, httpx.TimeoutException) as exc:
        logger.warning("[TemplateGeneratorAI] timeout Claude: %s", exc)
        return None
    except Exception as exc:
        logger.warning("[TemplateGeneratorAI] erreur Claude: %s", exc)
        return None

    parts: list[str] = []
    for block in response.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    raw = "".join(parts)
    html = _extract_html_from_response(raw)
    err = _validate_generated_html(html)
    if err:
        logger.warning(
            "[TemplateGeneratorAI] HTML invalide (%s) — repli catalogue | extrait=%s",
            err,
            raw[:400],
        )
        return None

    template_id = _make_template_id(project_type, sector)
    placeholders = sorted(set(_PLACEHOLDER_RE.findall(html)))
    summary = (
        f"Template HTML généré ({template_id}) — {len(html)} car., "
        f"{len(placeholders)} placeholders"
    )
    logger.info("[TemplateGeneratorAI] OK | %s | placeholders=%s", template_id, placeholders[:12])
    return TemplateGeneratorResult(
        html=html,
        template_id=template_id,
        summary=summary,
    )


def design_system_json_for_log(design_system: Any | None) -> str:
    if isinstance(design_system, dict):
        return json.dumps(design_system, ensure_ascii=False)[:500]
    return ""

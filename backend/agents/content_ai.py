"""
ContentAI — Agent 3.

Enrichit le template via un bloc CSS premium généré par Claude Sonnet (injection dans <head>),
puis remplit les placeholders avec le contenu client réel
(research, secteur, design system) et applique les post-traitements.
"""

from __future__ import annotations

import html as html_lib
import json
import logging
import os
import re
from typing import Any

import httpx
from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from agents.design_system_ai import (
    DesignSystemJSON,
    apply_design_system_to_html,
)
from tools.project_title import short_project_name
from agents.template_ai import fill_template_placeholders
from core.agent_contract import AgentContractError, AgentResult
from agents.content_slots import (
    build_app_slots,
    build_default_contact_slots,
    build_desktop_slots,
    build_ecommerce_slots,
    build_reservation_slots,
    _RESERVATION_TEAM,
    _team_placeholder_slots,
    ensure_contact_slots,
)
from tools.html_markdown import strip_markdown_code_fences
from tools.client_content_profile import (
    build_client_content_profile,
    humanize_sector_label,
    resolve_client_business_name,
    sanitize_city,
)
from config import get_settings
from prompts import CONTENT_AI_SYSTEM_PROMPT
from security.llm_secrets import get_effective_llm_key

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

logger = logging.getLogger(__name__)

_AGENT_ID = "content_ai"
_AGENT_NAME = "ContentAI"

CONTENT_AI_MODEL = os.getenv("COREMIND_SONNET_MODEL", "claude-sonnet-4-5")
CONTENT_AI_MAX_TOKENS = 4000
CONTENT_AI_CLAUDE_TIMEOUT_SECONDS = 120.0

_anthropic_http_client = httpx.AsyncClient(timeout=CONTENT_AI_CLAUDE_TIMEOUT_SECONDS)
_anthropic_client = AsyncAnthropic(
    api_key=get_effective_llm_key("ANTHROPIC_API_KEY", get_settings()) or "",
    http_client=_anthropic_http_client,
)

_PLACEHOLDER_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def _clean_client_name(text: str) -> str:
    """Retire les caractères Markdown (# * `) des noms affichés dans les placeholders."""
    return re.sub(r"[#*`]", "", (text or "")).strip()


def inject_stripe(html: str, payment_config: Any | None) -> str:
    """
    Injecte Stripe Checkout dans un HTML si payment_config l'exige.

    - Ajoute <script src="https://js.stripe.com/v3/"></script> dans <head>
    - Injecte payment_config["frontend_code"] avant </body>
    - Remplace {{STRIPE_PUBLIC_KEY}} par pk_test_VOTRE_CLE_STRIPE (+ commentaire FR)
    """
    if not (html or "").strip():
        return html
    if not isinstance(payment_config, dict):
        return html
    payment_type = str(payment_config.get("payment_type") or "").strip().lower()
    if not payment_type or payment_type == "none":
        return html

    out = html
    stripe_script = '<script src="https://js.stripe.com/v3/"></script>'
    if "js.stripe.com/v3" not in out:
        if "</head>" in out.lower():
            out = re.sub(
                r"</head>",
                f"  {stripe_script}\n</head>",
                out,
                count=1,
                flags=re.I,
            )
        else:
            out = f"{stripe_script}\n{out}"

    if "{{STRIPE_PUBLIC_KEY}}" in out:
        out = out.replace("{{STRIPE_PUBLIC_KEY}}", "pk_test_VOTRE_CLE_STRIPE")
        if "cf-stripe-public-key-hint" not in out and "</head>" in out.lower():
            hint = (
                '<!-- cf-stripe-public-key-hint: remplacez pk_test_VOTRE_CLE_STRIPE '
                "par votre clé publique Stripe (pk_...) -->\n"
            )
            out = re.sub(r"</head>", f"  {hint}</head>", out, count=1, flags=re.I)

    frontend_code = payment_config.get("frontend_code")
    if isinstance(frontend_code, str) and frontend_code.strip():
        if "cf-stripe-frontend-code" not in out:
            if "<script" in frontend_code.lower():
                snippet = f"\n<!-- cf-stripe-frontend-code -->\n{frontend_code.strip()}\n"
            else:
                snippet = (
                    "\n<script id=\"cf-stripe-frontend-code\">\n"
                    f"{frontend_code.strip()}\n"
                    "</script>\n"
                )
            if "</body>" in out.lower():
                out = re.sub(r"</body>", f"{snippet}</body>", out, count=1, flags=re.I)
            else:
                out = f"{out}\n{snippet}"

    js_len = (
        len(frontend_code.strip())
        if isinstance(frontend_code, str) and frontend_code.strip()
        else 0
    )
    logger.info(
        "[PaymentAI] Stripe injecté: type=%s (%d caractères JS)",
        payment_type,
        js_len,
    )
    return out

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
    project_name: str = "",
) -> dict[str, str]:
    """Construit toutes les valeurs de placeholders pour ContentAI."""
    research = _coerce_research_dict(research_content)
    ds = _design_system_slots(design_system)
    client_name = _clean_client_name(client_name)
    project_name = _clean_client_name(project_name)
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
    if project_name:
        brand = project_name
    elif user_prompt:
        inferred = short_project_name(user_prompt)
        if inferred and inferred != "Projet":
            brand = inferred
    brand = _clean_client_name(brand)
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
            sector=sector or research.get("secteur") or profile.sector,
        )
    if tid.startswith("app_"):
        slots = build_app_slots(
            tid, brand, ds, sector_label, user_prompt=user_prompt
        )
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
        "CLIENT_TAGLINE": html_lib.escape(hero_subtitle),
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
    if tid == "vitrine_sante":
        health_team = _RESERVATION_TEAM["reservation_sante"]
        slots.update(_team_placeholder_slots(health_team))
        slots["TEAM_MEMBER_1_BIO"] = html_lib.escape(
            f"{sector_label} · 12 ans d'expérience"
        )
        slots["TEAM_MEMBER_2_BIO"] = html_lib.escape(
            "Approche bienveillante et à l'écoute"
        )
        slots["TEAM_MEMBER_3_BIO"] = html_lib.escape(f"Accueil · {city_clean}")
    if tid == "vitrine_nautisme":
        slots["FLEET_1_NAME"] = html_lib.escape("Voilier 8m")
        slots["FLEET_1_DESC"] = html_lib.escape(
            "Jusqu'à 6 personnes · Skipper optionnel"
        )
        slots["FLEET_2_NAME"] = html_lib.escape("Catamaran")
        slots["FLEET_2_DESC"] = html_lib.escape("Sorties journée · Équipement complet")
        slots["FLEET_3_NAME"] = html_lib.escape("Semi-rigide")
        slots["FLEET_3_DESC"] = html_lib.escape(f"Découverte côte · {city_clean}")
    return slots


def _apply_design_system_css(html: str, design_system: Any | None) -> str:
    """Injecte / renforce les variables CSS de la loi visuelle."""
    try:
        return apply_design_system_to_html(html, design_system, log_prefix="ContentAI")
    except Exception as exc:
        logger.warning(
            "[ContentAI] apply design system ignoré — HTML conservé: %s",
            exc,
        )
        return html


def _apply_project_name_to_html(html: str, project_name: str) -> str:
    """Applique le nom court au <title> et au premier <h1> (sidebar / hero)."""
    name = (project_name or "").strip()
    if not name or len(name) < 2:
        return html
    escaped = html_lib.escape(name)
    out = html
    if re.search(r"<title[^>]*>", out, re.I):
        out = re.sub(
            r"(<title[^>]*>)[^<]*(</title>)",
            rf"\1{escaped}\2",
            out,
            count=1,
            flags=re.I,
        )
    elif "</head>" in out.lower():
        out = re.sub(
            r"</head>",
            f"  <title>{escaped}</title>\n</head>",
            out,
            count=1,
            flags=re.I,
        )
    if re.search(r"<h1[^>]*>", out, re.I):
        out = re.sub(
            r"(<h1[^>]*>)[^<]{0,240}(</h1>)",
            rf"\1{escaped}\2",
            out,
            count=1,
            flags=re.I,
        )
    return out


def _fix_action_links(html: str) -> str:
    """Remplace href='#' inertes par des ancres ou actions réelles."""
    html = re.sub(
        r'(<a[^>]*class=["\'][^"\']*logo[^"\']*["\'][^>]*)href=["\'][^"\']*["\']',
        r'\1 href="#top"',
        html,
        count=1,
        flags=re.I,
    )
    html = re.sub(
        r'<a([^>]*)\shref=["\']#["\']([^>]*)>',
        r'<a\1 href="#top"\2>',
        html,
        flags=re.I,
    )
    html = re.sub(
        r'<form([^>]*)action=["\']#["\']([^>]*)>',
        r'<form\1 action="javascript:void(0)"\2>',
        html,
        flags=re.I,
    )
    if 'id="top"' not in html and "<body" in html.lower():
        html = re.sub(r"<body([^>]*)>", r'<body\1 id="top">', html, count=1, flags=re.I)
    return html


def _anthropic_api_key() -> str | None:
    key = get_effective_llm_key("ANTHROPIC_API_KEY", get_settings())
    return (key or "").strip() or None


def _serialize_design_system(design_system: Any | None) -> dict[str, Any]:
    if design_system is None:
        return {}
    if isinstance(design_system, DesignSystemJSON):
        return design_system.to_contract_dict()
    if isinstance(design_system, dict):
        return design_system
    if hasattr(design_system, "model_dump"):
        return design_system.model_dump(mode="json")
    return {}


_CONTENT_AI_CSS_RULE_HEADER = (
    "RÈGLE ABSOLUE : génère UNIQUEMENT du CSS pur. "
    "Zéro Markdown, zéro ##, zéro **, zéro texte explicatif. "
    "Commence directement par <style> et termine par </style>."
)

_CONTENT_PREMIUM_IO_SCRIPT = """
<script id="cf-content-premium-io">
(function () {
  var els = document.querySelectorAll(".reveal");
  if (!els.length || !("IntersectionObserver" in window)) {
    els.forEach(function (el) { el.classList.add("visible"); });
    return;
  }
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) {
        e.target.classList.add("visible");
        io.unobserve(e.target);
      }
    });
  }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
  els.forEach(function (el) { io.observe(el); });
})();
</script>
""".strip()


def _plain_text_for_claude(text: str) -> str:
    """Retire le Markdown des champs texte envoyés à Claude (pas de ##, **, `)."""
    t = (text or "").strip()
    if not t:
        return ""
    t = re.sub(r"```[\w]*\n?", "", t)
    t = t.replace("```", "")
    t = re.sub(r"^#+\s+", "", t, flags=re.MULTILINE)
    t = t.replace("**", "").replace("__", "")
    t = re.sub(r"`([^`]*)`", r"\1", t)
    t = re.sub(r"^\s*[-*+]\s+", "", t, flags=re.MULTILINE)
    return t.strip()


def _is_markdown_artifact_line(line: str) -> bool:
    """Ligne Markdown (# titre, * liste, ` code) — pas du CSS."""
    stripped = line.lstrip()
    if not stripped:
        return False
    return stripped[0] in "#*`"


def _strip_markdown_lines_from_css(inner: str) -> str:
    kept: list[str] = []
    for line in inner.splitlines():
        if _is_markdown_artifact_line(line):
            continue
        kept.append(line)
    return "\n".join(kept).strip()


def _sanitize_premium_style_block(style_block: str) -> str:
    """Supprime les lignes Markdown résiduelles dans le bloc <style>."""
    block = (style_block or "").strip()
    if not block:
        return ""
    match = re.match(
        r"(<style\b[^>]*>)([\s\S]*?)(</style>)",
        block,
        flags=re.I,
    )
    if not match:
        inner_clean = _strip_markdown_lines_from_css(block)
        if not inner_clean:
            return ""
        return f'<style id="cf-content-premium">\n{inner_clean}\n</style>'

    open_tag, inner, close_tag = match.groups()
    inner_clean = _strip_markdown_lines_from_css(inner)
    if not inner_clean:
        return ""
    return f"{open_tag}\n{inner_clean}\n{close_tag}"


def _is_valid_premium_style_block(style_block: str) -> bool:
    s = (style_block or "").strip()
    if not s:
        return False
    return bool(
        re.match(r"<style\b", s, re.I) and re.search(r"</style>\s*$", s, re.I)
    )


def _build_content_ai_css_user_prompt(
    *,
    design_system: Any | None,
    user_prompt: str,
    client_name: str,
    sector: str,
    city: str,
    research_content: Any | None,
    template_id: str,
    project_name: str,
) -> str:
    research = _coerce_research_dict(research_content)
    ds_json = json.dumps(
        _serialize_design_system(design_system),
        ensure_ascii=False,
        indent=2,
    )
    research_json = json.dumps(research, ensure_ascii=False, indent=2)
    name = _plain_text_for_claude(client_name)
    project = re.sub(r"[#*`]", "", (project_name or client_name or "")).strip()
    sector_plain = _plain_text_for_claude(sector)
    city_plain = _plain_text_for_claude(city)
    tid = _plain_text_for_claude(template_id)
    description = _plain_text_for_claude(user_prompt) or (
        f"Site vitrine {sector_plain} pour {name} à {city_plain}."
    )
    return (
        f"{_CONTENT_AI_CSS_RULE_HEADER}\n\n"
        f"template_id: {tid}\n"
        f"client_name: {name}\n"
        f"project_name: {project}\n"
        f"sector: {sector_plain}\n"
        f"city: {city_plain}\n\n"
        f"description_projet:\n{description[:12000]}\n\n"
        f"design_system (JSON):\n{ds_json}\n\n"
        f"research_brief (JSON):\n{research_json}"
    )


def _extract_style_block(text: str) -> str:
    """Extrait le bloc <style> de la réponse Claude."""
    cleaned = strip_markdown_code_fences(text or "").strip()
    if not cleaned:
        return ""
    if re.search(r"<style\b", cleaned, flags=re.I):
        match = re.search(
            r"(<style\b[^>]*>[\s\S]*?</style>)",
            cleaned,
            flags=re.I,
        )
        block = match.group(1).strip() if match else cleaned
    else:
        block = f'<style id="cf-content-premium">\n{cleaned}\n</style>'
    if 'id="cf-content-premium"' not in block.lower():
        block = re.sub(
            r"<style\b",
            '<style id="cf-content-premium"',
            block,
            count=1,
            flags=re.I,
        )
    return _sanitize_premium_style_block(block)


def _inject_premium_css_into_head(html: str, style_block: str) -> str:
    """Injecte le CSS premium avant </head> ; le markup existant est inchangé."""
    style_block = _sanitize_premium_style_block(style_block)
    if not _is_valid_premium_style_block(style_block):
        return html
    out = html
    if 'id="cf-content-premium"' not in out.lower():
        if re.search(r"</head>", out, flags=re.I):
            out = re.sub(
                r"</head>",
                f"  {style_block}\n</head>",
                out,
                count=1,
                flags=re.I,
            )
        else:
            out = f"{style_block}\n{out}"
    if 'id="cf-content-premium-io"' not in out.lower():
        if re.search(r"</body>", out, flags=re.I):
            out = re.sub(
                r"</body>",
                f"  {_CONTENT_PREMIUM_IO_SCRIPT}\n</body>",
                out,
                count=1,
                flags=re.I,
            )
        else:
            out = f"{out}\n{_CONTENT_PREMIUM_IO_SCRIPT}"
    return out


async def _enrich_template_html_with_claude(
    *,
    template_html: str,
    design_system: Any | None,
    user_prompt: str,
    client_name: str,
    sector: str,
    city: str,
    research_content: Any | None,
    template_id: str,
    project_name: str,
) -> str | None:
    """
    Génère un bloc CSS premium via Claude et l'injecte dans <head>.
    Le HTML existant (placeholders inclus) n'est pas réécrit.
    Retourne None si clé absente ou échec (repli sur template brut).
    """
    if os.environ.get("CONTENT_AI_ENRICH_LLM", "1").strip().lower() in (
        "0",
        "false",
        "no",
        "off",
    ):
        return None

    api_key = _anthropic_api_key()
    if not api_key:
        logger.debug("[ContentAI] ANTHROPIC_API_KEY absente — enrichissement LLM ignoré")
        return None

    user_message = _build_content_ai_css_user_prompt(
        design_system=design_system,
        user_prompt=user_prompt,
        client_name=client_name,
        sector=sector,
        city=city,
        research_content=research_content,
        template_id=template_id,
        project_name=project_name,
    )
    logger.info("[ContentAI] Appel Claude Sonnet (CSS premium)...")
    try:
        response = await _anthropic_client.messages.create(
            model=CONTENT_AI_MODEL,
            max_tokens=CONTENT_AI_MAX_TOKENS,
            system=CONTENT_AI_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
    except (TimeoutError, httpx.TimeoutException) as exc:
        logger.warning(
            "[ContentAI] Claude Sonnet timeout (%.0fs) — repli template brut: %s",
            CONTENT_AI_CLAUDE_TIMEOUT_SECONDS,
            exc,
        )
        return None
    except Exception as exc:
        logger.warning("[ContentAI] Claude Sonnet échoué — repli template brut: %s", exc)
        return None

    parts: list[str] = []
    for block in response.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    raw = "".join(parts)
    style_block = _extract_style_block(raw)
    if not style_block or len(style_block) < 80:
        logger.warning(
            "[ContentAI] Bloc <style> Claude invalide ou trop court (%d car.) — repli template",
            len(style_block),
        )
        return None
    html_out = _inject_premium_css_into_head(template_html, style_block)
    logger.info(
        "[ContentAI] Claude OK - CSS %d caractères injecté(s) dans le template",
        len(style_block),
    )
    return html_out


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


async def fill_template_content(
    *,
    template_html: str,
    client_name: str,
    sector: str,
    city: str = "",
    research_content: Any | None = None,
    design_system: Any | None = None,
    payment_config: Any | None = None,
    user_prompt: str = "",
    template_id: str = "vitrine_default",
    project_name: str = "",
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
    client_name = _clean_client_name(client_name)
    project_name = _clean_client_name(project_name)
    resolved_name = _clean_client_name(
        resolve_client_business_name(
            client_name or profile.company_name or "",
            sector=sector or profile.sector or "",
            city=city_hint,
            user_prompt=user_prompt,
        )
    )
    if len(resolved_name.strip()) < 2:
        return AgentResult.failure(
            agent_id=_AGENT_ID,
            agent_name=_AGENT_NAME,
            code="missing_client_name",
            message="client_name obligatoire pour ContentAI.",
        )

    try:
        display_name = _clean_client_name(project_name or resolved_name)
        slots = build_content_slots(
            client_name=display_name,
            sector=sector,
            city=city,
            template_html=template_html,
            research_content=research_content,
            design_system=design_system,
            user_prompt=user_prompt,
            template_id=template_id,
            project_name=project_name,
        )
        working_html = template_html
        enriched = await _enrich_template_html_with_claude(
            template_html=template_html,
            design_system=design_system,
            user_prompt=user_prompt,
            client_name=display_name,
            sector=sector or research_dict.get("secteur") or profile.sector or "",
            city=city_hint,
            research_content=research_content,
            template_id=template_id,
            project_name=project_name,
        )
        if enriched:
            working_html = enriched
        html, filled, missing = fill_template_placeholders(working_html, slots)
        if missing:
            return AgentResult.failure(
                agent_id=_AGENT_ID,
                agent_name=_AGENT_NAME,
                code="missing_placeholders",
                message=f"Placeholders non remplis : {', '.join(missing)}",
            )
        html = strip_markdown_code_fences(html)
        html = _apply_design_system_css(html, design_system)
        title_name = (project_name or "").strip()
        if not title_name and slots.get("CLIENT_NAME"):
            title_name = html_lib.unescape(str(slots["CLIENT_NAME"]))
        html = _apply_project_name_to_html(html, title_name)
        html = _fix_action_links(html)
        if (template_id or "").startswith("ecommerce_"):
            from tools.ecommerce_product_images import ensure_ecommerce_product_thumbnails

            html = ensure_ecommerce_product_thumbnails(html, template_id)
        if (template_id or "").startswith("app_"):
            from tools.app_template_enhance import enhance_app_template_html

            html = enhance_app_template_html(html)
        from tools.standalone_demo_html import inject_demo_link_navigation_script

        html = inject_demo_link_navigation_script(html)
        html = inject_stripe(html, payment_config)
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
        result = await fill_template_content(
            template_html=kwargs.get("template_html") or "",
            client_name=kwargs.get("client_name") or "",
            sector=kwargs.get("sector") or "",
            city=kwargs.get("city") or "",
            research_content=kwargs.get("research_content"),
            design_system=kwargs.get("design_system"),
            payment_config=kwargs.get("payment_config"),
            user_prompt=prompt,
            template_id=kwargs.get("template_id") or "vitrine_default",
            project_name=kwargs.get("project_name") or "",
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
        payment_config: Any | None = None,
        user_prompt: str = "",
        template_id: str = "vitrine_default",
        project_name: str = "",
    ) -> AgentResult[ContentFillResult]:
        return await fill_template_content(
            template_html=template_html,
            client_name=client_name,
            sector=sector,
            city=city,
            research_content=research_content,
            design_system=design_system,
            payment_config=payment_config,
            user_prompt=user_prompt,
            template_id=template_id,
            project_name=project_name,
        )

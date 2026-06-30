"""
DesignSystemAI ΓÇö Agent 1 (priorit├⌐ absolue).

G├⌐n├¿re un design system complet AVANT toute g├⌐n├⌐ration de code.
Le JSON produit est la LOI VISUELLE du projet ΓÇö transmis ├á tous les agents suivants.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from agents.base_agent import BaseAgent
from agents.coremind_agent import ProjectType
from core.agent_contract import AgentContractError, AgentResult
from tools.client_content_profile import sanitize_brand_name
from tools.toolbox_branding import google_fonts_stylesheet_url, hex_to_hsl_channels
from tools.toolbox_sectors import detect_sector_from_prompt, normalize_sector_key

logger = logging.getLogger(__name__)

_AGENT_ID = "design_system"
_AGENT_NAME = "DesignSystemAI"

_HEX_RE = re.compile(r"^#([0-9A-Fa-f]{6})$")

_CONTRACT_KEYS = frozenset({
    "fonts",
    "colors",
    "spacing",
    "border_radius",
    "shadows",
    "style_keywords",
    "google_fonts_url",
})

VisualFamily = Literal[
    "alimentaire",
    "marin_sport",
    "artisan_batiment",
    "sante_bien_etre",
    "tech_digital",
    "beaute_mode",
    "juridique_finance",
    "automobile",
]

FontStyle = Literal["artisanal", "moderne", "elegant"]

# Couleurs par famille (primary, secondary, accent) ΓÇö loi sectorielle
_FAMILY_PALETTES: dict[VisualFamily, dict[str, str]] = {
    # Boulangerie / restaurant / alimentaire ΓÇö cr├¿me, brun, dor├⌐
    "alimentaire": {
        "primary": "#5C3A21",
        "secondary": "#FCF7F0",
        "accent": "#C9A84C",
    },
    # Nautisme / sport ΓÇö bleus profonds, blancs
    "marin_sport": {
        "primary": "#0A3D62",
        "secondary": "#FFFFFF",
        "accent": "#1E88E5",
    },
    # Artisan / b├ótiment ΓÇö gris ardoise, orange
    "artisan_batiment": {
        "primary": "#4A5568",
        "secondary": "#F7FAFC",
        "accent": "#DD6B20",
    },
    # Sant├⌐ / bien-├¬tre ΓÇö verts doux, blancs
    "sante_bien_etre": {
        "primary": "#2D6A4F",
        "secondary": "#FFFFFF",
        "accent": "#74C69D",
    },
    # Tech / digital ΓÇö sombres, n├⌐on subtil
    "tech_digital": {
        "primary": "#0D1117",
        "secondary": "#161B22",
        "accent": "#58A6FF",
    },
    # Beaut├⌐ / mode ΓÇö rose poudr├⌐, noir ├⌐l├⌐gant
    "beaute_mode": {
        "primary": "#1A1A1A",
        "secondary": "#FDF2F8",
        "accent": "#E8B4B8",
    },
    # Juridique / finance ΓÇö navy, or, blanc
    "juridique_finance": {
        "primary": "#1C2833",
        "secondary": "#FFFFFF",
        "accent": "#C9A84C",
    },
    # Automobile ΓÇö industriel, pro, moderne (gris acier + orange)
    "automobile": {
        "primary": "#2C3E50",
        "secondary": "#FFFFFF",
        "accent": "#E67E22",
    },
}

# Polices Google par style
_FONT_STYLES: dict[FontStyle, tuple[str, str]] = {
    "artisanal": ("Playfair Display", "Lato"),
    "moderne": ("Inter", "Space Grotesk"),
    "elegant": ("Cormorant", "Raleway"),
}

# Famille ΓåÆ style typo par d├⌐faut
_FAMILY_FONT_STYLE: dict[VisualFamily, FontStyle] = {
    "alimentaire": "artisanal",
    "marin_sport": "moderne",
    "artisan_batiment": "artisanal",
    "sante_bien_etre": "elegant",
    "tech_digital": "moderne",
    "beaute_mode": "elegant",
    "juridique_finance": "elegant",
    "automobile": "moderne",
}

_FAMILY_STYLE_KEYWORDS: dict[VisualFamily, list[str]] = {
    "alimentaire": ["artisanal", "chaleureux", "gourmand", "moderne"],
    "marin_sport": ["moderne", "dynamique", "marin", "├⌐nergique"],
    "artisan_batiment": ["artisanal", "robuste", "authentique", "moderne"],
    "sante_bien_etre": ["apaisant", "clair", "humain", "rassurant"],
    "tech_digital": ["moderne", "├⌐pur├⌐", "innovant", "pr├⌐cis"],
    "beaute_mode": ["├⌐l├⌐gant", "raffin├⌐", "doux", "premium"],
    "juridique_finance": ["prestige", "confiance", "├⌐l├⌐gant", "moderne"],
    "automobile": ["industriel", "professionnel", "moderne", "robuste"],
}

_SECTOR_TO_FAMILY: dict[str, VisualFamily] = {
    "restauration": "alimentaire",
    "nautisme": "marin_sport",
    "sport": "marin_sport",
    "artisanat": "artisan_batiment",
    "sante": "sante_bien_etre",
    "technologie": "tech_digital",
    "beaute": "beaute_mode",
    "immobilier": "juridique_finance",
    "commerce": "juridique_finance",
    "education": "sante_bien_etre",
    "automobile": "automobile",
}

# Mots-cl├⌐s prompt ΓåÆ famille (priorit├⌐ haute)
_PROMPT_FAMILY_RULES: tuple[tuple[tuple[str, ...], VisualFamily], ...] = (
    (
        (
            "boulangerie",
            "boulanger",
            "patisserie",
            "p├ótisserie",
            "restaurant",
            "restauration",
            "brasserie",
            "bistro",
            "traiteur",
            "alimentaire",
            "caf├⌐",
            "cafe",
            "food",
            "cuisine",
            "menu",
        ),
        "alimentaire",
    ),
    (
        ("nautisme", "yacht", "voilier", "marina", "voile", "nautical", "bateau"),
        "marin_sport",
    ),
    (
        ("fitness", "gym", "crossfit", "musculation", "coach sportif"),
        "marin_sport",
    ),
    (
        (
            "artisan",
            "artisanat",
            "menuisier",
            "plombier",
            "├⌐lectricien",
            "electricien",
            "ma├ºon",
            "macon",
            "b├ótiment",
            "batiment",
            "btp",
            "chantier",
            "couvreur",
        ),
        "artisan_batiment",
    ),
    (
        (
            "sant├⌐",
            "sante",
            "m├⌐decin",
            "medecin",
            "clinique",
            "dentiste",
            "bien-├¬tre",
            "bien etre",
            "wellness",
            "spa",
            "kin├⌐",
            "kine",
        ),
        "sante_bien_etre",
    ),
    (
        (
            "tech",
            "digital",
            "saas",
            "startup",
            "logiciel",
            "software",
            "agence web",
            "d├⌐veloppement",
            "developpement",
            "ia ",
            " intelligence artificielle",
        ),
        "tech_digital",
    ),
    (
        (
            "beaut├⌐",
            "beaute",
            "coiffeur",
            "coiffure",
            "mode",
            "fashion",
            "esth├⌐tique",
            "esthetique",
            "salon",
            "maquillage",
        ),
        "beaute_mode",
    ),
    (
        (
            "avocat",
            "juridique",
            "notaire",
            "finance",
            "comptable",
            "cabinet",
            "banque",
            "assurance",
            "investissement",
        ),
        "juridique_finance",
    ),
)

_VISUAL_LAW_HEADER = (
    "## LOI VISUELLE DU PROJET (DesignSystemAI ΓÇö non n├⌐gociable)\n"
    "Ce JSON est transmis ├á TOUS les agents (Research, Builder, CoreMind, "
    "Vision, BugHunter, Export). Interdiction de d├⌐vier des couleurs, polices et tokens.\n\n"
)


class DesignSystemFonts(BaseModel):
    heading: str = Field(min_length=1)
    body: str = Field(min_length=1)


class DesignSystemColors(BaseModel):
    primary: str
    secondary: str
    accent: str
    bg: str
    text: str
    text_light: str


class DesignSystemSpacing(BaseModel):
    section: str
    element: str


class DesignSystemJSON(BaseModel):
    """JSON contractuel ΓÇö loi visuelle unique du projet."""

    fonts: DesignSystemFonts
    colors: DesignSystemColors
    spacing: DesignSystemSpacing
    border_radius: str
    shadows: str
    style_keywords: list[str] = Field(min_length=3)
    google_fonts_url: str

    @field_validator("google_fonts_url")
    @classmethod
    def _url_must_be_google_fonts(cls, value: str) -> str:
        url = (value or "").strip()
        if not url.startswith("https://fonts.googleapis.com/"):
            raise ValueError("google_fonts_url doit pointer vers fonts.googleapis.com")
        return url

    @field_validator("shadows", "border_radius")
    @classmethod
    def _non_empty_token(cls, value: str) -> str:
        if not (value or "").strip():
            raise ValueError("valeur obligatoire")
        return value.strip()

    def to_contract_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


DesignSystemDocument = DesignSystemJSON


def resolve_visual_family(
    sector: str,
    user_prompt: str = "",
) -> VisualFamily:
    """D├⌐duit la famille visuelle (couleurs) depuis le secteur et le prompt."""
    blob = f"{sector} {user_prompt}".lower()
    for keywords, family in _PROMPT_FAMILY_RULES:
        if any(kw in blob for kw in keywords):
            return family
    sector_key = normalize_sector_key(sector or "")
    return _SECTOR_TO_FAMILY.get(sector_key, "juridique_finance")


def resolve_font_style(
    family: VisualFamily,
    style_keywords: list[str] | None = None,
) -> FontStyle:
    """Polices selon le style : artisanal, moderne ou ├⌐l├⌐gant."""
    if style_keywords:
        joined = " ".join(style_keywords).lower()
        if "artisanal" in joined or "authentique" in joined or "gourmand" in joined:
            return "artisanal"
        if "├⌐l├⌐gant" in joined or "elegant" in joined or "raffin├⌐" in joined or "prestige" in joined:
            return "elegant"
        if "moderne" in joined or "├⌐pur├⌐" in joined or "innovant" in joined:
            return "moderne"
    return _FAMILY_FONT_STYLE[family]


def _normalize_hex(value: str, *, field_name: str) -> str:
    raw = (value or "").strip()
    if not raw.startswith("#"):
        raw = f"#{raw}"
    if not _HEX_RE.match(raw):
        raise AgentContractError(
            agent_id=_AGENT_ID,
            code="invalid_color",
            message=f"Couleur invalide pour {field_name}: {value!r}",
        )
    return raw.upper()


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _relative_luminance(hex_color: str) -> float:
    r, g, b = _hex_to_rgb(hex_color)
    channels = []
    for c in (r, g, b):
        x = c / 255.0
        channels.append(x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _is_light(hex_color: str) -> bool:
    return _relative_luminance(hex_color) > 0.55


def _mix_hex(a: str, b: str, ratio: float) -> str:
    ar, ag, ab = _hex_to_rgb(a)
    br, bg, bb = _hex_to_rgb(b)
    t = max(0.0, min(1.0, ratio))
    r = round(ar + (br - ar) * t)
    g = round(ag + (bg - ag) * t)
    bl = round(ab + (bb - ab) * t)
    return f"#{r:02X}{g:02X}{bl:02X}"


def _derive_contract_colors(
    primary: str,
    secondary: str,
    accent: str,
    *,
    family: VisualFamily,
) -> DesignSystemColors:
    primary = _normalize_hex(primary, field_name="primary")
    secondary = _normalize_hex(secondary, field_name="secondary")
    accent = _normalize_hex(accent, field_name="accent")

    if family == "tech_digital":
        bg = secondary
        text = "#E6EDF3"
        text_light = "#8B949E"
    elif family == "beaute_mode":
        bg = secondary
        text = primary
        text_light = _mix_hex(text, bg, 0.45)
    else:
        if _is_light(secondary):
            bg = secondary
        else:
            bg = _mix_hex(secondary, "#FFFFFF", 0.88)
        text = "#1A1A1A" if _is_light(bg) else "#F5F5F4"
        text_light = _mix_hex(text, bg, 0.42)

    return DesignSystemColors(
        primary=primary,
        secondary=secondary,
        accent=accent,
        bg=bg,
        text=text,
        text_light=text_light,
    )


def _parse_palette_preference(palette_preference: Any | None) -> dict[str, str] | None:
    if palette_preference is None:
        return None
    if hasattr(palette_preference, "model_dump"):
        data = palette_preference.model_dump()
    elif isinstance(palette_preference, dict):
        data = palette_preference
    else:
        return None
    out: dict[str, str] = {}
    for key in ("primary", "secondary", "accent"):
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            out[key] = val.strip()
    return out or None


def _palette_from_firecrawl(firecrawl_data: Any | None) -> dict[str, str] | None:
    """Extrait primary/secondary/accent depuis firecrawl_result (palette ou couleurs)."""
    if not isinstance(firecrawl_data, dict):
        return None
    raw = firecrawl_data.get("palette") or firecrawl_data.get("couleurs")
    if not isinstance(raw, dict):
        return None
    key_map = {
        "primary": ("primary", "textPrimary"),
        "secondary": ("secondary", "background"),
        "accent": ("accent",),
    }
    out: dict[str, str] = {}
    for target, candidates in key_map.items():
        for key in candidates:
            val = raw.get(key)
            if isinstance(val, str) and val.strip().startswith("#"):
                out[target] = val.strip()
                break
    return out or None


def _fonts_from_firecrawl(firecrawl_data: Any | None) -> tuple[str, str] | None:
    if not isinstance(firecrawl_data, dict):
        return None
    fonts = firecrawl_data.get("fonts")
    if not isinstance(fonts, dict):
        return None
    heading = fonts.get("heading") or fonts.get("title")
    body = fonts.get("body") or fonts.get("text")
    if isinstance(heading, str) and isinstance(body, str) and heading.strip() and body.strip():
        return heading.strip(), body.strip()
    return None


def _resolve_palette(
    family: VisualFamily,
    palette_preference: Any | None,
    *,
    firecrawl_data: Any | None = None,
) -> tuple[dict[str, str], str]:
    base = dict(_FAMILY_PALETTES[family])
    pref = _parse_palette_preference(palette_preference)
    if pref:
        base = {**base, **pref}
        source = "user_preference" if len(pref) == 3 else f"merged:{family}"
    else:
        source = f"sector_family:{family}"
    fc = _palette_from_firecrawl(firecrawl_data)
    if fc:
        merged = {**base, **fc}
        logger.info(
            "[DesignSystemAI] Couleurs appliqu├⌐es: %s %s %s",
            merged.get("primary"),
            merged.get("secondary"),
            merged.get("accent"),
        )
        return merged, "firecrawl"
    return base, source


def _spacing_for_project(project_type: str) -> DesignSystemSpacing:
    if project_type in ("saas_dashboard", "application_web", "api_backend"):
        return DesignSystemSpacing(section="64px", element="16px")
    if project_type in ("landing_page", "site_web"):
        return DesignSystemSpacing(section="80px", element="24px")
    return DesignSystemSpacing(section="72px", element="20px")


def _border_radius_for_family(family: VisualFamily) -> str:
    if family in ("alimentaire", "beaute_mode", "artisan_batiment"):
        return "12px"
    if family == "tech_digital":
        return "6px"
    return "8px"


def _shadow_for_colors(colors: DesignSystemColors) -> str:
    if _is_light(colors.bg):
        return "0 4px 24px rgba(0,0,0,0.08)"
    return "0 4px 24px rgba(0,0,0,0.35)"


def design_system_to_css_variables(doc: DesignSystemJSON) -> str:
    """Variables CSS ΓÇö injection Builder / TemplateEngine."""
    c = doc.colors
    p_hsl = hex_to_hsl_channels(c.primary)
    s_hsl = hex_to_hsl_channels(c.secondary)
    a_hsl = hex_to_hsl_channels(c.accent)
    heading_font = doc.fonts.heading.replace("'", "\\'")
    body_font = doc.fonts.body.replace("'", "\\'")
    return f""":root {{
  --cf-primary: {c.primary};
  --cf-secondary: {c.secondary};
  --cf-accent: {c.accent};
  --cf-bg: {c.bg};
  --cf-text: {c.text};
  --cf-text-light: {c.text_light};
  --cf-font-heading: '{heading_font}', serif;
  --cf-font-body: '{body_font}', sans-serif;
  --cf-section-spacing: {doc.spacing.section};
  --cf-element-spacing: {doc.spacing.element};
  --cf-radius: {doc.border_radius};
  --cf-shadow: {doc.shadows};
  --color-primary: {c.primary};
  --color-secondary: {c.secondary};
  --color-accent: {c.accent};
  --font-heading: '{heading_font}', serif;
  --font-body: '{body_font}', sans-serif;
  --border-radius: {doc.border_radius};
  --color-border-radius: {doc.border_radius};
  --primary: {p_hsl};
  --secondary: {s_hsl};
  --accent: {a_hsl};
}}
"""


def _sync_template_css_variables(html: str, doc: DesignSystemJSON) -> str:
    """Aligne les variables :root existantes sur le design system."""
    try:
        c = doc.colors
        f = doc.fonts
        heading_esc = f.heading.replace("'", "\\'")
        body_esc = f.body.replace("'", "\\'")
        replacements: tuple[tuple[str, str], ...] = (
            (r"(--color-primary\s*:\s*)[^;]+", rf"\1{c.primary}"),
            (r"(--color-secondary\s*:\s*)[^;]+", rf"\1{c.secondary}"),
            (r"(--color-accent\s*:\s*)[^;]+", rf"\1{c.accent}"),
            (r"(--font-heading\s*:\s*)[^;]+", rf"\1'{heading_esc}', serif"),
            (r"(--font-body\s*:\s*)[^;]+", rf"\1'{body_esc}', sans-serif"),
            (r"(--border-radius\s*:\s*)[^;]+", rf"\1{doc.border_radius}"),
            (r"(--primary\s*:\s*)[^;]+", rf"\1{c.primary}"),
            (r"(--secondary\s*:\s*)[^;]+", rf"\1{c.secondary}"),
            (r"(--accent\s*:\s*)[^;]+", rf"\1{c.accent}"),
            (r"(--font-h\s*:\s*)[^;]+", rf"\1'{heading_esc}', serif"),
            (r"(--font-b\s*:\s*)[^;]+", rf"\1'{body_esc}', sans-serif"),
        )
        out = html
        for pattern, repl in replacements:
            out = re.sub(pattern, repl, out, flags=re.I)
        return out
    except Exception as exc:
        logger.warning(
            "[DesignSystemAI] sync variables CSS ignor├⌐e ΓÇö HTML conserv├⌐: %s",
            exc,
        )
        return html


def apply_design_system_to_html(
    html: str,
    design_system: DesignSystemJSON | dict[str, Any] | None,
    *,
    log_prefix: str = "BuilderAI",
) -> str:
    """Injecte la loi visuelle (variables + Google Fonts) dans le HTML final."""
    if not (html or "").strip() or design_system is None:
        return html
    if isinstance(design_system, dict):
        try:
            doc = DesignSystemJSON.model_validate(design_system)
        except Exception:
            return html
    elif isinstance(design_system, DesignSystemJSON):
        doc = design_system
    else:
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

    html = _sync_template_css_variables(html, doc)
    logger.info(
        "[%s] design system inject├⌐: primary=%s font=%s/%s radius=%s",
        log_prefix,
        doc.colors.primary,
        doc.fonts.heading,
        doc.fonts.body,
        doc.border_radius,
    )
    return html


def inject_design_system_into_html(html: str, doc: DesignSystemJSON | dict[str, Any]) -> str:
    """Injecte la loi visuelle (variables + Google Fonts) dans un document HTML."""
    return apply_design_system_to_html(html, doc, log_prefix="DesignSystemAI")


def _validate_contract(doc: DesignSystemJSON) -> None:
    payload = doc.to_contract_dict()
    missing = sorted(_CONTRACT_KEYS - set(payload.keys()))
    if missing:
        raise AgentContractError(
            agent_id=_AGENT_ID,
            code="incomplete_json",
            message=f"Cl├⌐s JSON manquantes : {', '.join(missing)}",
        )
    for key in ("primary", "secondary", "accent", "bg", "text", "text_light"):
        _normalize_hex(getattr(doc.colors, key), field_name=key)


def build_design_system(
    *,
    sector: str,
    client_name: str,
    palette_preference: Any | None = None,
    project_type: str | ProjectType,
    user_prompt: str = "",
    firecrawl_data: Any | None = None,
) -> AgentResult[DesignSystemJSON]:
    """Produit le JSON contractuel ou ├⌐choue explicitement."""
    raw_name = (client_name or "").strip()
    if len(raw_name) < 2:
        return AgentResult.failure(
            agent_id=_AGENT_ID,
            agent_name=_AGENT_NAME,
            code="missing_client_name",
            message="client_name obligatoire pour le design system.",
            detail="Fournissez un nom d'entreprise court (pas le prompt entier).",
        )

    sector_key = normalize_sector_key(sector or "")
    if not sector_key:
        sector_key = detect_sector_from_prompt(
            user_prompt,
            project_type=_coerce_project_type(project_type),
        )

    if isinstance(project_type, ProjectType):
        pt_value = project_type.value
    else:
        pt_value = str(project_type or ProjectType.SITE_WEB.value).strip().lower()

    try:
        family = resolve_visual_family(sector_key, user_prompt)
        style_keywords = list(_FAMILY_STYLE_KEYWORDS[family])
        font_style: FontStyle = "moderne"
        if family == "automobile":
            font_style = "moderne"
            heading, body = ("Roboto Condensed", "Roboto")
        else:
            font_style = resolve_font_style(family, style_keywords)
            heading, body = _FONT_STYLES[font_style]

        fc_fonts = _fonts_from_firecrawl(firecrawl_data)
        if fc_fonts:
            heading, body = fc_fonts
            logger.info(
                "[DesignSystemAI] polices Firecrawl appliqu├⌐es: %s / %s",
                heading,
                body,
            )

        palette, palette_source = _resolve_palette(
            family, palette_preference, firecrawl_data=firecrawl_data
        )
        colors = _derive_contract_colors(
            palette["primary"],
            palette["secondary"],
            palette["accent"],
            family=family,
        )
        fonts = DesignSystemFonts(heading=heading, body=body)
        gfonts = google_fonts_stylesheet_url(heading, body)
        if not gfonts:
            gfonts = "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap"

        doc = DesignSystemJSON(
            fonts=fonts,
            colors=colors,
            spacing=_spacing_for_project(pt_value),
            border_radius=_border_radius_for_family(family),
            shadows=_shadow_for_colors(colors),
            style_keywords=style_keywords,
            google_fonts_url=gfonts,
        )
        _validate_contract(doc)
    except AgentContractError as exc:
        return AgentResult.failure(
            agent_id=_AGENT_ID,
            agent_name=_AGENT_NAME,
            code=exc.code,
            message=exc.message,
            detail=exc.detail,
        )
    except Exception as exc:
        logger.exception("[DesignSystemAI] ├⌐chec g├⌐n├⌐ration")
        return AgentResult.failure(
            agent_id=_AGENT_ID,
            agent_name=_AGENT_NAME,
            code="design_system_failed",
            message="Impossible de produire le design system.",
            detail=str(exc),
        )

    logger.info(
        "[DesignSystemAI] OK | family=%s | fonts=%s/%s | primary=%s | %s",
        family,
        heading,
        body,
        colors.primary,
        palette_source,
    )
    return AgentResult.success(
        agent_id=_AGENT_ID,
        agent_name=_AGENT_NAME,
        data=doc,
        meta={
            "palette_source": palette_source,
            "visual_family": family,
            "font_style": font_style,
            "project_type": pt_value,
            "sector": sector_key,
            "client_name": sanitize_brand_name(raw_name, user_prompt=user_prompt),
        },
    )


def _coerce_project_type(project_type: str | ProjectType) -> ProjectType | None:
    if isinstance(project_type, ProjectType):
        return project_type
    try:
        return ProjectType(str(project_type).strip().lower())
    except ValueError:
        return None


def format_design_system_for_prompt(doc: DesignSystemJSON | dict[str, Any] | None) -> str:
    """Bloc loi visuelle inject├⌐ dans TOUS les prompts agents."""
    if doc is None:
        return ""
    if isinstance(doc, dict):
        if not _CONTRACT_KEYS.issubset(set(doc.keys())):
            return ""
        try:
            doc = DesignSystemJSON.model_validate(doc)
        except Exception:
            return ""

    return (
        f"\n{_VISUAL_LAW_HEADER}"
        f"```json\n{doc.model_dump_json(indent=2)}\n```\n"
        f"Polices impos├⌐es : {doc.fonts.heading} (titres) + {doc.fonts.body} (corps). "
        f"Couleurs impos├⌐es : primary {doc.colors.primary}, bg {doc.colors.bg}. "
        f"Style : {', '.join(doc.style_keywords)}.\n\n"
    )


class DesignSystemAgent(BaseAgent):
    @property
    def agent_id(self) -> str:
        return _AGENT_ID

    @property
    def name(self) -> str:
        return _AGENT_NAME

    async def run(self, prompt: str, **kwargs: Any) -> str:
        result = await self.generate(
            sector=kwargs.get("sector") or "",
            client_name=kwargs.get("client_name") or "",
            palette_preference=kwargs.get("palette_preference"),
            project_type=kwargs.get("project_type") or ProjectType.SITE_WEB,
            user_prompt=prompt,
        )
        if not result.ok or result.data is None:
            err = result.error
            raise AgentContractError(
                agent_id=_AGENT_ID,
                code=err.code if err else "failure",
                message=err.message if err else "├ëchec DesignSystemAI",
                detail=err.detail if err else None,
            )
        return result.data.model_dump_json(indent=2)

    async def generate(
        self,
        *,
        sector: str,
        client_name: str,
        palette_preference: Any | None = None,
        project_type: str | ProjectType,
        user_prompt: str = "",
        firecrawl_data: Any | None = None,
    ) -> AgentResult[DesignSystemJSON]:
        return build_design_system(
            sector=sector,
            client_name=client_name,
            palette_preference=palette_preference,
            project_type=project_type,
            user_prompt=user_prompt,
            firecrawl_data=firecrawl_data,
        )

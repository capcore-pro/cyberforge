"""
DesignSystemAI — Agent 1 (priorité absolue).

Génère un design system complet AVANT toute génération de code.
Le JSON produit est la LOI VISUELLE du projet — transmis à tous les agents suivants.
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

# Couleurs par famille (primary, secondary, accent) — loi sectorielle
_FAMILY_PALETTES: dict[VisualFamily, dict[str, str]] = {
    # Boulangerie / restaurant / alimentaire — crème, brun, doré
    "alimentaire": {
        "primary": "#5C3A21",
        "secondary": "#FCF7F0",
        "accent": "#C9A84C",
    },
    # Nautisme / sport — bleus profonds, blancs
    "marin_sport": {
        "primary": "#0A3D62",
        "secondary": "#FFFFFF",
        "accent": "#1E88E5",
    },
    # Artisan / bâtiment — gris ardoise, orange
    "artisan_batiment": {
        "primary": "#4A5568",
        "secondary": "#F7FAFC",
        "accent": "#DD6B20",
    },
    # Santé / bien-être — verts doux, blancs
    "sante_bien_etre": {
        "primary": "#2D6A4F",
        "secondary": "#FFFFFF",
        "accent": "#74C69D",
    },
    # Tech / digital — sombres, néon subtil
    "tech_digital": {
        "primary": "#0D1117",
        "secondary": "#161B22",
        "accent": "#58A6FF",
    },
    # Beauté / mode — rose poudré, noir élégant
    "beaute_mode": {
        "primary": "#1A1A1A",
        "secondary": "#FDF2F8",
        "accent": "#E8B4B8",
    },
    # Juridique / finance — navy, or, blanc
    "juridique_finance": {
        "primary": "#1C2833",
        "secondary": "#FFFFFF",
        "accent": "#C9A84C",
    },
    # Automobile — industriel, pro, moderne (gris acier + orange)
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

# Famille → style typo par défaut
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
    "marin_sport": ["moderne", "dynamique", "marin", "énergique"],
    "artisan_batiment": ["artisanal", "robuste", "authentique", "moderne"],
    "sante_bien_etre": ["apaisant", "clair", "humain", "rassurant"],
    "tech_digital": ["moderne", "épuré", "innovant", "précis"],
    "beaute_mode": ["élégant", "raffiné", "doux", "premium"],
    "juridique_finance": ["prestige", "confiance", "élégant", "moderne"],
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

# Mots-clés prompt → famille (priorité haute)
_PROMPT_FAMILY_RULES: tuple[tuple[tuple[str, ...], VisualFamily], ...] = (
    (
        (
            "boulangerie",
            "boulanger",
            "patisserie",
            "pâtisserie",
            "restaurant",
            "restauration",
            "brasserie",
            "bistro",
            "traiteur",
            "alimentaire",
            "café",
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
            "électricien",
            "electricien",
            "maçon",
            "macon",
            "bâtiment",
            "batiment",
            "btp",
            "chantier",
            "couvreur",
        ),
        "artisan_batiment",
    ),
    (
        (
            "santé",
            "sante",
            "médecin",
            "medecin",
            "clinique",
            "dentiste",
            "bien-être",
            "bien etre",
            "wellness",
            "spa",
            "kiné",
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
            "développement",
            "developpement",
            "ia ",
            " intelligence artificielle",
        ),
        "tech_digital",
    ),
    (
        (
            "beauté",
            "beaute",
            "coiffeur",
            "coiffure",
            "mode",
            "fashion",
            "esthétique",
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
    "## LOI VISUELLE DU PROJET (DesignSystemAI — non négociable)\n"
    "Ce JSON est transmis à TOUS les agents (Research, Stitch, Builder, CoreMind, "
    "Vision, BugHunter, Export). Interdiction de dévier des couleurs, polices et tokens.\n\n"
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
    """JSON contractuel — loi visuelle unique du projet."""

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
    """Déduit la famille visuelle (couleurs) depuis le secteur et le prompt."""
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
    """Polices selon le style : artisanal, moderne ou élégant."""
    if style_keywords:
        joined = " ".join(style_keywords).lower()
        if "artisanal" in joined or "authentique" in joined or "gourmand" in joined:
            return "artisanal"
        if "élégant" in joined or "elegant" in joined or "raffiné" in joined or "prestige" in joined:
            return "elegant"
        if "moderne" in joined or "épuré" in joined or "innovant" in joined:
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


def _resolve_palette(
    family: VisualFamily,
    palette_preference: Any | None,
) -> tuple[dict[str, str], str]:
    base = dict(_FAMILY_PALETTES[family])
    pref = _parse_palette_preference(palette_preference)
    if not pref:
        return base, f"sector_family:{family}"
    merged = {**base, **pref}
    source = "user_preference" if len(pref) == 3 else f"merged:{family}"
    return merged, source


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
    """Variables CSS — injection Builder / TemplateEngine."""
    c = doc.colors
    p_hsl = hex_to_hsl_channels(c.primary)
    s_hsl = hex_to_hsl_channels(c.secondary)
    a_hsl = hex_to_hsl_channels(c.accent)
    return f""":root {{
  --cf-primary: {c.primary};
  --cf-secondary: {c.secondary};
  --cf-accent: {c.accent};
  --cf-bg: {c.bg};
  --cf-text: {c.text};
  --cf-text-light: {c.text_light};
  --cf-font-heading: '{doc.fonts.heading}', serif;
  --cf-font-body: '{doc.fonts.body}', sans-serif;
  --cf-section-spacing: {doc.spacing.section};
  --cf-element-spacing: {doc.spacing.element};
  --cf-radius: {doc.border_radius};
  --cf-shadow: {doc.shadows};
  --primary: {p_hsl};
  --secondary: {s_hsl};
  --accent: {a_hsl};
}}
"""


def design_system_to_stitch_palette(
    doc: DesignSystemJSON | dict[str, Any] | None,
) -> dict[str, str]:
    """Palette triple pour StitchAI."""
    if doc is None:
        return {}
    if isinstance(doc, dict):
        colors = doc.get("colors") or {}
    else:
        colors = doc.colors.model_dump()
    return {
        "primary": colors.get("primary", ""),
        "secondary": colors.get("secondary", ""),
        "accent": colors.get("accent", ""),
    }


def inject_design_system_into_html(html: str, doc: DesignSystemJSON | dict[str, Any]) -> str:
    """Injecte la loi visuelle (variables + Google Fonts) dans un document HTML."""
    if isinstance(doc, dict):
        try:
            doc = DesignSystemJSON.model_validate(doc)
        except Exception:
            return html
    css_block = design_system_to_css_variables(doc)
    link = f'<link rel="stylesheet" href="{doc.google_fonts_url}" />\n'
    style = f"<style id=\"cf-design-system\">{css_block}</style>\n"
    snippet = link + style
    lower = html.lower()
    if "cf-design-system" in lower:
        return html
    if "</head>" in lower:
        return re.sub(r"</head>", f"  {snippet}</head>", html, count=1, flags=re.I)
    return snippet + html


def _validate_contract(doc: DesignSystemJSON) -> None:
    payload = doc.to_contract_dict()
    missing = sorted(_CONTRACT_KEYS - set(payload.keys()))
    if missing:
        raise AgentContractError(
            agent_id=_AGENT_ID,
            code="incomplete_json",
            message=f"Clés JSON manquantes : {', '.join(missing)}",
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
) -> AgentResult[DesignSystemJSON]:
    """Produit le JSON contractuel ou échoue explicitement."""
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
        if family == "automobile":
            heading, body = ("Roboto Condensed", "Roboto")
        else:
            font_style = resolve_font_style(family, style_keywords)
            heading, body = _FONT_STYLES[font_style]

        palette, palette_source = _resolve_palette(family, palette_preference)
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
        logger.exception("[DesignSystemAI] échec génération")
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
    """Bloc loi visuelle injecté dans TOUS les prompts agents."""
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
        f"Polices imposées : {doc.fonts.heading} (titres) + {doc.fonts.body} (corps). "
        f"Couleurs imposées : primary {doc.colors.primary}, bg {doc.colors.bg}. "
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
                message=err.message if err else "Échec DesignSystemAI",
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
    ) -> AgentResult[DesignSystemJSON]:
        return build_design_system(
            sector=sector,
            client_name=client_name,
            palette_preference=palette_preference,
            project_type=project_type,
            user_prompt=user_prompt,
        )

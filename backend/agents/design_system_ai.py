"""
DesignSystemAI — loi visuelle contractuelle (tokens CSS) pour GeneratorAI et DeployAI.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

STYLE_FAMILIES: dict[str, dict[str, str]] = {
    "premium_light": {
        "bg": "#ffffff",
        "surface": "#f8fafc",
        "text_primary": "#1a1a2e",
        "text_secondary": "#64748b",
        "radius_lg": "20px",
        "shadow": "0 4px 24px rgba(0,0,0,0.08)",
    },
    "premium_dark": {
        "bg": "#0f1117",
        "surface": "#1e2535",
        "text_primary": "#e2e8f0",
        "text_secondary": "#8892a4",
        "radius_lg": "20px",
        "shadow": "0 4px 24px rgba(0,0,0,0.4)",
    },
    "premium_commerce": {
        "bg": "#fafafa",
        "surface": "#ffffff",
        "text_primary": "#1a1a2e",
        "text_secondary": "#6b7280",
        "radius_lg": "16px",
        "shadow": "0 2px 16px rgba(0,0,0,0.1)",
    },
    "nature_warm": {
        "bg": "#f8f5f0",
        "surface": "#ffffff",
        "text_primary": "#2d2016",
        "text_secondary": "#78614a",
        "radius_lg": "12px",
        "shadow": "0 4px 16px rgba(0,0,0,0.06)",
    },
    "compact_dark": {
        "bg": "#0f1117",
        "surface": "#161b27",
        "text_primary": "#e2e8f0",
        "text_secondary": "#8892a4",
        "radius_lg": "8px",
        "shadow": "none",
    },
}

PROJECT_TYPE_FAMILY: dict[str, str] = {
    "vitrine_next": "premium_light",
    "ecommerce": "premium_commerce",
    "saas_dashboard": "premium_commerce",
    "site_reservation": "nature_warm",
    "application_web": "premium_dark",
    "real_app": "premium_dark",
    "extension_navigateur": "compact_dark",
    "application_desktop": "premium_dark",
}

PROJECT_TYPE_FONTS: dict[str, dict[str, str]] = {
    "vitrine_next": {"heading": "Playfair Display", "body": "Inter"},
    "ecommerce": {"heading": "Inter", "body": "Inter"},
    "saas_dashboard": {"heading": "Inter", "body": "Inter"},
    "site_reservation": {"heading": "Playfair Display", "body": "Inter"},
    "application_web": {"heading": "Inter", "body": "Inter"},
    "real_app": {"heading": "Inter", "body": "Inter"},
    "extension_navigateur": {"heading": "Inter", "body": "Inter"},
    "application_desktop": {"heading": "Inter", "body": "Inter"},
}

DEFAULT_FONTS = {"heading": "Playfair Display", "body": "Inter"}

SECTOR_PRIMARY_HINTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("boulangerie", "artisanat", "artisan"), "#5C3A21"),
    (("nautisme", "marine", "bateau"), "#0A3D62"),
    (("tech", "digital", "logiciel", "saas"), "#6366f1"),
    (("santé", "sante", "médical", "medical", "bien-être", "bien-etre"), "#0ea5e9"),
    (("mode", "vêtements", "vetements", "beauté", "beaute"), "#d4a843"),
    (("restauration", "food", "restaurant"), "#dc2626"),
    (("nature", "bio", "écologie", "ecologie"), "#16a34a"),
    (("immobilier",), "#0f766e"),
)

_HEX_RE = re.compile(r"^#([0-9a-fA-F]{6})$")

_CONTRACT_KEYS = frozenset(
    {
        "style_family",
        "colors",
        "fonts",
        "radius",
        "shadow",
        "spacing",
        "css_variables",
    }
)


def _normalize_pt(project_type: Any) -> str:
    if hasattr(project_type, "value"):
        project_type = project_type.value
    return str(project_type or "").strip().lower().replace("-", "_")


def _sector_text(brief: dict[str, Any]) -> str:
    parts = [
        str(brief.get("sector") or ""),
        str(brief.get("description") or ""),
        str(brief.get("prompt") or ""),
    ]
    return " ".join(parts).lower()


def _suggest_primary_from_sector(brief: dict[str, Any]) -> str | None:
    text = _sector_text(brief)
    for keywords, color in SECTOR_PRIMARY_HINTS:
        if any(kw in text for kw in keywords):
            return color
    return None


def _parse_hex(hex_color: str) -> tuple[int, int, int] | None:
    m = _HEX_RE.match((hex_color or "").strip())
    if not m:
        return None
    h = m.group(1)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _clamp(v: int) -> int:
    return max(0, min(255, v))


def _to_hex(r: int, g: int, b: int) -> str:
    return f"#{_clamp(r):02x}{_clamp(g):02x}{_clamp(b):02x}"


def _lighten(hex_color: str, percent: float = 15.0) -> str:
    rgb = _parse_hex(hex_color)
    if not rgb:
        return hex_color
    r, g, b = rgb
    factor = percent / 100.0
    return _to_hex(
        int(r + (255 - r) * factor),
        int(g + (255 - g) * factor),
        int(b + (255 - b) * factor),
    )


def _darken(hex_color: str, percent: float = 20.0) -> str:
    rgb = _parse_hex(hex_color)
    if not rgb:
        return hex_color
    r, g, b = rgb
    factor = 1.0 - percent / 100.0
    return _to_hex(int(r * factor), int(g * factor), int(b * factor))


def _overlay_rgba(hex_color: str, opacity: float = 0.8) -> str:
    rgb = _parse_hex(hex_color)
    if not rgb:
        return f"rgba(37, 99, 235, {opacity})"
    r, g, b = rgb
    return f"rgba({r}, {g}, {b}, {opacity})"


def resolve_style_family(brief: dict[str, Any]) -> str:
    pt = _normalize_pt(brief.get("project_type"))
    return PROJECT_TYPE_FAMILY.get(pt, "premium_light")


def resolve_visual_family(sector: str, user_prompt: str = "") -> str:
    """Compatibilité tests legacy — retourne une étiquette sectorielle."""
    text = f"{sector} {user_prompt}".lower()
    if any(k in text for k in ("boulangerie", "patisserie", "alimentaire")):
        return "alimentaire"
    if any(k in text for k in ("tech", "saas", "digital", "startup")):
        return "tech_digital"
    return "general"


def _resolve_fonts(brief: dict[str, Any]) -> dict[str, str]:
    pt = _normalize_pt(brief.get("project_type"))
    fonts = dict(PROJECT_TYPE_FONTS.get(pt, DEFAULT_FONTS))
    custom = str(brief.get("font") or "").strip()
    if custom and custom.lower() not in ("inter",):
        fonts["heading"] = custom
    return fonts


def _brief_from_args(brief: dict[str, Any] | None, kwargs: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = dict(brief or {})
    if kwargs:
        mapping = {
            "sector": kwargs.get("sector"),
            "client_name": kwargs.get("client_name"),
            "project_type": kwargs.get("project_type"),
            "user_prompt": kwargs.get("user_prompt"),
            "description": kwargs.get("user_prompt") or kwargs.get("description"),
        }
        pref = kwargs.get("palette_preference")
        if pref is not None:
            if hasattr(pref, "primary"):
                mapping["couleur_primaire"] = getattr(pref, "primary", None)
                mapping["couleur_secondaire"] = getattr(pref, "secondary", None)
            elif isinstance(pref, dict):
                mapping["couleur_primaire"] = pref.get("primary")
                mapping["couleur_secondaire"] = pref.get("secondary")
        for k, v in mapping.items():
            if v is not None and v != "":
                out[k] = v
    return out


def build_design_system(
    brief: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Construit le JSON design_system depuis le brief (ou kwargs legacy).
    """
    b = _brief_from_args(brief, kwargs)
    style_family = resolve_style_family(b)
    family = STYLE_FAMILIES[style_family]

    primary = str(b.get("couleur_primaire") or b.get("primary_color") or "").strip()
    if not primary or not _parse_hex(primary):
        suggested = _suggest_primary_from_sector(b)
        primary = suggested or "#2563EB"

    secondary = str(b.get("couleur_secondaire") or b.get("secondary_color") or "").strip()
    if not secondary or not _parse_hex(secondary):
        secondary = family["surface"]

    fonts = _resolve_fonts(b)
    accent = _lighten(primary, 15.0)
    primary_dark = _darken(primary, 20.0)
    overlay = _overlay_rgba(primary, 0.8)
    shadow_card = family["shadow"]
    shadow_hover = (
        "0 8px 32px rgba(0,0,0,0.12)"
        if style_family != "compact_dark"
        else "none"
    )

    colors = {
        "primary": primary,
        "secondary": secondary,
        "accent": accent,
        "primary_dark": primary_dark,
        "overlay": overlay,
        "background": family["bg"],
        "surface": family["surface"],
        "text_primary": family["text_primary"],
        "text_secondary": family["text_secondary"],
        "success": "#16a34a",
        "warning": "#f59e0b",
        "error": "#dc2626",
    }

    radius_lg = family["radius_lg"]
    design_system: dict[str, Any] = {
        "style_family": style_family,
        "colors": colors,
        "fonts": fonts,
        "radius": {
            "sm": "4px",
            "md": "8px",
            "lg": radius_lg,
            "pill": "50px",
        },
        "shadow": {
            "card": shadow_card,
            "hover": shadow_hover,
        },
        "spacing": {
            "unit": "8px",
            "section": "80px",
        },
    }
    design_system["css_variables"] = design_system_to_css_variables(design_system)
    return design_system


def design_system_to_css_variables(design_system: dict[str, Any]) -> str:
    """Génère le bloc :root { --color-* ... }."""
    ds = _as_dict(design_system)
    colors = ds.get("colors") or {}
    fonts = ds.get("fonts") or {}
    radius = ds.get("radius") or {}
    shadow = ds.get("shadow") or {}
    spacing = ds.get("spacing") or {}

    lines = [
        "/* cf-design-system */",
        ":root {",
        f"  --color-primary: {colors.get('primary', '#2563EB')};",
        f"  --color-secondary: {colors.get('secondary', '#F8FAFC')};",
        f"  --color-accent: {colors.get('accent', colors.get('primary', '#2563EB'))};",
        f"  --color-bg: {colors.get('background', '#ffffff')};",
        f"  --color-surface: {colors.get('surface', '#f8fafc')};",
        f"  --color-text-primary: {colors.get('text_primary', '#1a1a2e')};",
        f"  --color-text-secondary: {colors.get('text_secondary', '#64748b')};",
        f"  --color-success: {colors.get('success', '#16a34a')};",
        f"  --color-warning: {colors.get('warning', '#f59e0b')};",
        f"  --color-error: {colors.get('error', '#dc2626')};",
        f"  --color-primary-dark: {colors.get('primary_dark', colors.get('primary', '#2563EB'))};",
        f"  --color-overlay: {colors.get('overlay', 'rgba(37,99,235,0.8)')};",
        f"  --font-heading: '{fonts.get('heading', 'Playfair Display')}', serif;",
        f"  --font-body: '{fonts.get('body', 'Inter')}', sans-serif;",
        f"  --radius-sm: {radius.get('sm', '4px')};",
        f"  --radius-md: {radius.get('md', '8px')};",
        f"  --radius-lg: {radius.get('lg', '20px')};",
        f"  --radius-pill: {radius.get('pill', '50px')};",
        f"  --shadow-card: {shadow.get('card', '0 4px 24px rgba(0,0,0,0.08)')};",
        f"  --shadow-hover: {shadow.get('hover', '0 8px 32px rgba(0,0,0,0.12)')};",
        f"  --spacing-unit: {spacing.get('unit', '8px')};",
        f"  --spacing-section: {spacing.get('section', '80px')};",
        "}",
    ]
    return "\n".join(lines)


def format_design_system_for_prompt(design_system: dict[str, Any]) -> str:
    ds = _as_dict(design_system)
    css = ds.get("css_variables") or design_system_to_css_variables(ds)
    fonts = ds.get("fonts") or {}
    family = ds.get("style_family", "premium_light")
    return (
        "## design_system\n"
        f"Famille : {family}\n"
        f"Polices : heading={fonts.get('heading', 'Playfair Display')}, "
        f"body={fonts.get('body', 'Inter')}\n\n"
        f"{css}\n\n"
        "Règles d'application :\n"
        "- Utilise --color-primary pour CTAs, liens actifs, accents\n"
        "- Utilise --color-bg comme fond global\n"
        "- Utilise --font-heading pour h1/h2/h3\n"
        "- Colle le bloc :root tel quel dans <style>"
    )


def inject_design_system_into_html(html: str, design_system: Any) -> str:
    """Injecte :root si --color-primary ou --font-heading absents."""
    raw = html or ""
    if not raw.strip():
        return raw

    ds = _as_dict(design_system)
    css_block = ds.get("css_variables") or design_system_to_css_variables(ds)
    low = raw.lower()

    has_primary = "--color-primary" in low
    has_font_heading = "--font-heading" in low
    if has_primary and has_font_heading:
        return raw

    style_open = re.search(r"<style\b[^>]*>", raw, re.I)
    if style_open:
        insert_at = style_open.end()
        injection = "\n" + css_block + "\n"
        return raw[:insert_at] + injection + raw[insert_at:]

    head_close = re.search(r"</head>", raw, re.I)
    snippet = f"<style>\n{css_block}\n</style>\n"
    if head_close:
        pos = head_close.start()
        return raw[:pos] + snippet + raw[pos:]
    return snippet + raw


def _as_dict(design_system: Any) -> dict[str, Any]:
    if isinstance(design_system, dict):
        return design_system
    if hasattr(design_system, "to_contract_dict"):
        return design_system.to_contract_dict()
    if hasattr(design_system, "model_dump"):
        return design_system.model_dump()
    return {}


def is_valid_design_system(design_system: dict[str, Any]) -> bool:
    ds = _as_dict(design_system)
    if ds.get("style_family") not in STYLE_FAMILIES:
        return False
    colors = ds.get("colors") or {}
    primary = str(colors.get("primary") or "")
    if not _HEX_RE.match(primary):
        return False
    if not colors.get("background"):
        return False
    fonts = ds.get("fonts") or {}
    if not fonts.get("heading") or not fonts.get("body"):
        return False
    css = ds.get("css_variables") or ""
    if ":root" not in css:
        return False
    return True


class DesignSystemAgent:
    """Wrapper pipeline V2."""

    def run(self, brief: dict[str, Any]) -> dict[str, Any]:
        try:
            ds = build_design_system(brief)
            if not is_valid_design_system(ds):
                logger.warning("[DesignSystemAI] design_system invalide — rebuild")
                return build_design_system(brief or {})
            return ds
        except Exception as exc:
            logger.exception("[DesignSystemAI] erreur: %s", exc)
            return build_design_system(brief or {})

    async def generate(self, **kwargs: Any) -> Any:
        """Compatibilité async legacy (template-first tests)."""
        from core.agent_contract import AgentResult

        brief = _brief_from_args(None, kwargs)
        if not str(brief.get("client_name") or "").strip():
            from core.agent_contract import AgentFailure, AgentStatus

            return AgentResult(
                agent_id="design_system_ai",
                agent_name="DesignSystemAI",
                status=AgentStatus.FAILURE,
                error=AgentFailure(
                    agent_id="design_system_ai",
                    code="missing_client_name",
                    message="client_name requis",
                ),
            )
        data = build_design_system(brief)
        return AgentResult.success(
            agent_id="design_system_ai",
            agent_name="DesignSystemAI",
            data=_DesignSystemDoc(data),
        )


class _DesignSystemDoc:
    """Adaptateur attributs pour tests / template-first legacy."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data
        colors = data.get("colors") or {}
        self.colors = _AttrMap(colors)
        self.fonts = _AttrMap(data.get("fonts") or {})
        self.style_keywords = [data.get("style_family", "")]
        self.style_family = data.get("style_family")

    def to_contract_dict(self) -> dict[str, Any]:
        return dict(self._data)


class _AttrMap:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data
        self.bg = data.get("background") or data.get("bg")
        self.primary = data.get("primary")
        self.accent = data.get("accent")
        self.text = data.get("text_primary")
        self.heading = data.get("heading")
        self.body = data.get("body")

    def __getattr__(self, name: str) -> Any:
        return self._data.get(name)


# Alias pydantic-like pour tests legacy
DesignSystemJSON = _DesignSystemDoc

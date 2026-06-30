"""
Catalogue templates sectoriels — project_type + pricing_category + secteur.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from agents.design_system_ai import resolve_visual_family
from tools.toolbox_sectors import normalize_sector_key

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "sectors"

# Catégories tarifaires en assemblage template-first (HTML vanilla).
TEMPLATE_FIRST_PRICING_CATEGORIES: frozenset[str] = frozenset(
    {
        "ecommerce",
        "site_reservation",
        "application_web",
        "application_desktop",
        "vitrine_next",
    }
)

_VITRINE_SECTOR_FILES: dict[str, str] = {
    "alimentaire": "vitrine_alimentaire.html",
    "restauration": "vitrine_alimentaire.html",
    "marin_sport": "vitrine_nautisme.html",
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
}

_ECOMMERCE_HINTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (
        (
            "boulanger",
            "pâtiss",
            "patiss",
            "pâtisserie",
            "patisserie",
            "épicerie",
            "alimentaire",
            "bio",
            "primeur",
            "gourmand",
            "chocolat",
        ),
        "ecommerce_alimentaire.html",
    ),
    (
        ("mode", "vêtement", "vetement", "prêt-à-porter", "pret", "fashion", "lingerie"),
        "ecommerce_mode.html",
    ),
)

_RESERVATION_HINTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("dentiste", "médecin", "medecin", "kiné", "kine", "ostéo", "osteo", "clinique", "santé", "sante"), "reservation_sante.html"),
    (("coiff", "salon", "beauté", "beaute", "spa", "esthétique", "esthetique"), "reservation_beaute.html"),
)

_APP_HINTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (
        (
            "garage",
            "réparation",
            "reparation",
            "véhicule",
            "vehicule",
            "atelier",
            "mécanique",
            "mecanique",
            "automobile",
            "voiture",
            "carrosserie",
        ),
        "app_dashboard.html",
    ),
    (("crm", "commercial", "prospect", "vente", "pipeline"), "app_crm.html"),
    (("dashboard", "analytics", "kpi", "statistique", "tableau de bord"), "app_dashboard.html"),
)

_DESKTOP_HINTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("artisan", "btp", "plomb", "électric", "electric", "chantier"), "desktop_artisan.html"),
    (("gestion", "stock", "facture", "devis", "erp", "compta"), "desktop_gestion.html"),
)

# Camping / hébergement touristique — vitrine générique, pas vitrine_alimentaire.
_VITRINE_HOSPITALITY_HINTS: tuple[str, ...] = (
    "camping",
    "hébergement touristique",
    "hebergement touristique",
    "gîte",
    "gite",
    "chalet",
    "chalets",
    "cabane",
    "cabanes",
    "tourisme",
    "hébergement",
    "hebergement",
)

# Famille de templates imposée par pricing_category (priorité absolue).
_CATEGORY_TO_FAMILY: dict[str, str] = {
    "ecommerce": "ecommerce",
    "site_reservation": "reservation",
    "application_web": "app",
    "application_desktop": "desktop",
    "vitrine_next": "vitrine",
}


def _blob(sector: str, user_prompt: str) -> str:
    return f"{normalize_sector_key(sector)} {user_prompt}".lower()


_APP_CRM_KEYWORDS = frozenset(
    {"crm", "commercial", "prospect", "vente", "pipeline"}
)


def _keyword_in_blob(blob: str, keyword: str, *, word_boundary: bool) -> bool:
    if not keyword:
        return False
    if word_boundary:
        return bool(
            re.search(rf"\b{re.escape(keyword)}\b", blob, flags=re.IGNORECASE)
        )
    return keyword in blob


def _match_hints(
    blob: str,
    hints: tuple[tuple[tuple[str, ...], str], ...],
    default: str,
    *,
    word_boundary_keywords: frozenset[str] | None = None,
) -> str:
    wb = word_boundary_keywords or frozenset()
    for keywords, filename in hints:
        for kw in keywords:
            if _keyword_in_blob(blob, kw, word_boundary=kw in wb):
                return filename
    return default


def _project_type_value(plan: Any) -> str:
    pt = getattr(plan, "project_type", None)
    return (pt.value if hasattr(pt, "value") else str(pt or "")).strip().lower()


def _resolve_template_family(category: str, pt_value: str) -> str:
    """
    Choisit la famille de templates (ecommerce, app, vitrine, …).
    pricing_category prime ; le secteur n'influence pas la famille, seulement le fichier dans la famille.
    """
    cat = (category or "").strip().lower()

    if pt_value == "extension_navigateur" or cat == "extension_navigateur":
        return "extension"

    # pricing_category prime — jamais ecommerce/app si site_reservation imposé.
    if cat == "site_reservation":
        return "reservation"
    if cat == "ecommerce":
        return "ecommerce"
    if cat == "application_desktop":
        return "desktop"
    if cat == "vitrine_next":
        return "vitrine"

    # Générateur CyberForge « E-commerce » (project_type saas_dashboard).
    if pt_value == "saas_dashboard":
        return "ecommerce"

    if cat == "application_web" or pt_value in (
        "application_web",
        "api_backend",
        "application_mobile",
    ):
        return "app"

    if pt_value == "application_desktop":
        return "desktop"
    if pt_value in ("site_web", "landing_page"):
        return "vitrine"
    return "vitrine"


def _prompt_forces_vitrine_default_hospitality(blob: str) -> bool:
    """Hébergement outdoor / tourisme → vitrine_default (évite vitrine_alimentaire)."""
    if any(h in blob for h in _VITRINE_HOSPITALITY_HINTS):
        return True
    if "hébergement" in blob or "hebergement" in blob:
        return any(
            ctx in blob
            for ctx in (
                "camping",
                "chalet",
                "gîte",
                "gite",
                "cabane",
                "touristique",
                "tourisme",
            )
        )
    return False


def resolve_vitrine_template_file(sector: str, user_prompt: str = "") -> str:
    blob = _blob(sector, user_prompt)
    if _prompt_forces_vitrine_default_hospitality(blob):
        logger.info(
            "[sector_template_catalog] hébergement/tourisme détecté → vitrine_default.html"
        )
        return "vitrine_default.html"
    family = resolve_visual_family(normalize_sector_key(sector), user_prompt)
    return (
        _VITRINE_SECTOR_FILES.get(family)
        or _VITRINE_SECTOR_FILES.get(normalize_sector_key(sector))
        or "vitrine_default.html"
    )


def resolve_template_family_from_plan(plan: Any) -> str:
    """Famille imposée par pricing_category / project_type (diagnostic pipeline)."""
    category = (getattr(plan, "pricing_category", None) or "").strip().lower()
    return _resolve_template_family(category, _project_type_value(plan))


def is_ecommerce_plan(plan: Any) -> bool:
    return resolve_template_family_from_plan(plan) == "ecommerce"


def is_reservation_plan(plan: Any) -> bool:
    return resolve_template_family_from_plan(plan) == "reservation"


def resolve_sector_template_from_plan(
    plan: Any,
    sector: str,
    user_prompt: str = "",
) -> tuple[str, str]:
    """
    Retourne (template_id, filename) selon pricing_category / project_type / secteur.
    Le secteur affine le choix à l'intérieur de la famille uniquement.
    """
    blob = _blob(sector, user_prompt)
    category = (getattr(plan, "pricing_category", None) or "").strip().lower()
    pt_value = _project_type_value(plan)
    family = _resolve_template_family(category, pt_value)

    if family == "extension":
        logger.info(
            "[sector_template_catalog] extension_navigateur — pas de template HTML sectoriel"
        )
        return "extension_chrome", "extension_chrome.html"

    if family == "ecommerce":
        filename = _match_hints(blob, _ECOMMERCE_HINTS, "ecommerce_default.html")
    elif family == "reservation":
        filename = _match_hints(blob, _RESERVATION_HINTS, "reservation_default.html")
    elif family == "desktop":
        filename = _match_hints(blob, _DESKTOP_HINTS, "desktop_default.html")
    elif family == "app":
        filename = _match_hints(
            blob,
            _APP_HINTS,
            "app_dashboard.html",
            word_boundary_keywords=_APP_CRM_KEYWORDS,
        )
    else:
        filename = resolve_vitrine_template_file(sector, user_prompt)

    template_id = Path(filename).stem
    logger.info(
        "[sector_template_catalog] pricing_category=%s project_type=%s family=%s → %s (%s)",
        category or "?",
        pt_value or "?",
        family,
        template_id,
        filename,
    )
    return template_id, filename


def load_sector_template_html_for_plan(
    plan: Any,
    sector: str,
    user_prompt: str = "",
) -> tuple[str, str, str]:
    """Charge le fichier HTML sectoriel attendu pour le plan (template_id, filename, html)."""
    from agents.template_ai import load_sector_template_html

    template_id, filename = resolve_sector_template_from_plan(plan, sector, user_prompt)
    return template_id, filename, load_sector_template_html(filename)


def is_template_first_pricing_category(category: str | None) -> bool:
    return (category or "").strip().lower() in TEMPLATE_FIRST_PRICING_CATEGORIES


def template_file_path(filename: str) -> Path:
    return _TEMPLATES_DIR / filename


def ensure_template_exists(filename: str) -> None:
    path = template_file_path(filename)
    if not path.is_file():
        raise FileNotFoundError(f"Template manquant : {path}")

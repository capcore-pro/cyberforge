"""Secteurs toolbox — palettes, typos et détection heuristique."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

SECTEURS: dict[str, dict[str, Any]] = {
    "restauration": {
        "palette": {"primary": "#8B2E1F", "secondary": "#F5E6D3", "accent": "#D4A853"},
        "typo": {"heading": "Playfair Display", "body": "Lato"},
        "composants": ["hero", "menu", "gallery", "testimonials", "contact", "hours"],
        "mots_cles_visuels": [
            "restaurant interior",
            "gourmet food plating",
            "chef kitchen",
            "wine dining",
            "cozy bistro",
        ],
    },
    "nautisme": {
        "palette": {"primary": "#0A3D62", "secondary": "#E8F4F8", "accent": "#F39C12"},
        "typo": {"heading": "Montserrat", "body": "Open Sans"},
        "composants": ["hero", "services", "fleet", "gallery", "testimonials", "contact"],
        "mots_cles_visuels": [
            "sailing yacht ocean",
            "marina harbor",
            "boat deck sunset",
            "nautical lifestyle",
            "coastal marina",
        ],
    },
    "immobilier": {
        "palette": {"primary": "#1C2833", "secondary": "#F4F6F7", "accent": "#C9A84C"},
        "typo": {"heading": "Cormorant Garamond", "body": "Source Sans 3"},
        "composants": ["hero", "listings", "features", "stats", "testimonials", "contact"],
        "mots_cles_visuels": [
            "luxury home exterior",
            "modern apartment interior",
            "real estate agent",
            "penthouse view",
            "family house garden",
        ],
    },
    "sante": {
        "palette": {"primary": "#1A5276", "secondary": "#EBF5FB", "accent": "#48C9B0"},
        "typo": {"heading": "Nunito Sans", "body": "Inter"},
        "composants": ["hero", "services", "team", "faq", "testimonials", "contact"],
        "mots_cles_visuels": [
            "medical clinic modern",
            "doctor patient care",
            "healthcare professional",
            "wellness spa calm",
            "dental office bright",
        ],
    },
    "artisanat": {
        "palette": {"primary": "#5D4037", "secondary": "#EFEBE9", "accent": "#FF8F00"},
        "typo": {"heading": "Libre Baskerville", "body": "Work Sans"},
        "composants": ["hero", "process", "gallery", "testimonials", "cta", "contact"],
        "mots_cles_visuels": [
            "craftsman workshop",
            "handmade woodworking",
            "artisan tools",
            "pottery studio",
            "custom furniture making",
        ],
    },
    "beaute": {
        "palette": {"primary": "#6C3483", "secondary": "#FDF2F8", "accent": "#E91E8C"},
        "typo": {"heading": "Cormorant", "body": "Raleway"},
        "composants": ["hero", "services", "pricing", "gallery", "testimonials", "contact"],
        "mots_cles_visuels": [
            "beauty salon interior",
            "skincare treatment",
            "makeup artist studio",
            "spa relaxation",
            "nail salon elegant",
        ],
    },
    "sport": {
        "palette": {"primary": "#1B4F72", "secondary": "#F0F3F4", "accent": "#E74C3C"},
        "typo": {"heading": "Oswald", "body": "Roboto"},
        "composants": ["hero", "programs", "stats", "team", "pricing", "contact"],
        "mots_cles_visuels": [
            "fitness gym training",
            "athlete action sport",
            "yoga studio class",
            "running outdoor",
            "team sports energy",
        ],
    },
    "technologie": {
        "palette": {"primary": "#0D1117", "secondary": "#F6F8FA", "accent": "#58A6FF"},
        "typo": {"heading": "Space Grotesk", "body": "IBM Plex Sans"},
        "composants": ["hero", "features", "stats", "pricing", "faq", "cta", "contact"],
        "mots_cles_visuels": [
            "tech startup office",
            "software developer laptop",
            "data center servers",
            "innovation workspace",
            "digital product mockup",
        ],
    },
    "education": {
        "palette": {"primary": "#154360", "secondary": "#FEF9E7", "accent": "#F4D03F"},
        "typo": {"heading": "Merriweather", "body": "Nunito"},
        "composants": ["hero", "programs", "team", "testimonials", "faq", "contact"],
        "mots_cles_visuels": [
            "classroom students learning",
            "university campus",
            "online education laptop",
            "library study",
            "teacher workshop",
        ],
    },
    "commerce": {
        "palette": {"primary": "#212F3D", "secondary": "#FFFFFF", "accent": "#E67E22"},
        "typo": {"heading": "Poppins", "body": "DM Sans"},
        "composants": ["hero", "products", "features", "testimonials", "newsletter", "contact"],
        "mots_cles_visuels": [
            "retail store interior",
            "ecommerce product showcase",
            "shopping boutique",
            "local shop storefront",
            "product packaging display",
        ],
    },
}

_SECTOR_ALIASES: dict[str, str] = {
    "santé": "sante",
    "beaute": "beaute",
    "beauté": "beaute",
    "éducation": "education",
    "education": "education",
}


def normalize_sector_key(nom: str) -> str:
    raw = nom.strip().lower().replace(" ", "_")
    if raw in SECTEURS:
        return raw
    alias = _SECTOR_ALIASES.get(raw) or _SECTOR_ALIASES.get(nom.strip().lower())
    if alias:
        return alias
    folded = unicodedata.normalize("NFD", raw)
    ascii_key = "".join(c for c in folded if unicodedata.category(c) != "Mn")
    if ascii_key in SECTEURS:
        return ascii_key
    return raw

_SECTOR_KEYWORDS: dict[str, tuple[str, ...]] = {
    "restauration": (
        "restaurant", "restauration", "boulangerie", "patisserie",
        "cafe", "brasserie", "bistro", "food", "cuisine", "menu", "chef",
    ),
    "nautisme": (
        "nautisme", "yacht", "voilier", "bateau", "marina", "port", "sailing", "nautical",
    ),
    "immobilier": (
        "immobilier", "real estate", "appartement", "maison", "location", "immobilier",
    ),
    "sante": (
        "sante", "medecin", "clinique", "dentiste", "spa", "wellness", "health", "medical",
    ),
    "artisanat": (
        "artisan", "artisanat", "menuisier", "plombier", "electricien", "craft", "workshop",
    ),
    "beaute": (
        "beaute", "coiffeur", "salon", "esthetique", "spa", "nail",
    ),
    "sport": (
        "sport", "fitness", "gym", "yoga", "coach", "musculation", "crossfit", "training",
    ),
    "technologie": (
        "tech", "technologie", "saas", "software", "digital", "startup", "agence web", "dev",
    ),
    "education": (
        "formation", "ecole", "cours", "coaching", "education", "training center",
    ),
    "commerce": (
        "boutique", "shop", "e-commerce", "ecommerce", "retail", "magasin", "store",
    ),
}

_PRICING_CATEGORY_SECTOR: dict[str, str] = {
    "ecommerce": "commerce",
    "site_reservation": "restauration",
    "vitrine_next": "commerce",
}

def _sector_for_project_type(project_type: Any) -> str | None:
    from agents.coremind_agent import ProjectType

    mapping: dict[ProjectType, str] = {
        ProjectType.SITE_WEB: "commerce",
        ProjectType.LANDING_PAGE: "commerce",
        ProjectType.APPLICATION_WEB: "technologie",
        ProjectType.SAAS_DASHBOARD: "technologie",
        ProjectType.API_BACKEND: "technologie",
        ProjectType.EXTENSION_NAVIGATEUR: "technologie",
        ProjectType.APPLICATION_DESKTOP: "technologie",
        ProjectType.APPLICATION_MOBILE: "technologie",
        ProjectType.PROJET_GENERIQUE: "commerce",
    }
    return mapping.get(project_type)


@dataclass(frozen=True)
class SectorBundle:
    nom: str
    palette: dict[str, str]
    typo: dict[str, str]
    composants: list[str]
    mots_cles_visuels: list[str]


def detect_sector_from_prompt(
    prompt: str,
    *,
    project_type: Any | None = None,
    pricing_category: str | None = None,
) -> str:
    """Détecte le secteur toolbox le plus probable à partir du prompt."""
    if pricing_category and pricing_category in _PRICING_CATEGORY_SECTOR:
        return _PRICING_CATEGORY_SECTOR[pricing_category]

    text = re.sub(r"\s+", " ", prompt.strip().lower())
    scores: dict[str, int] = {key: 0 for key in SECTEURS}
    for key, keywords in _SECTOR_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[key] = scores.get(key, 0) + len(kw.split()) + 1

    best_key, best_score = max(scores.items(), key=lambda item: item[1])
    if best_score > 0:
        return best_key
    if project_type is not None:
        mapped = _sector_for_project_type(project_type)
        if mapped:
            return mapped
    return "commerce"


def get_sector_bundle(sector_key: str) -> SectorBundle | None:
    key = normalize_sector_key(sector_key)
    data = SECTEURS.get(key)
    if not data:
        return None
    return SectorBundle(
        nom=key,
        palette=dict(data["palette"]),
        typo=dict(data["typo"]),
        composants=list(data["composants"]),
        mots_cles_visuels=list(data["mots_cles_visuels"]),
    )



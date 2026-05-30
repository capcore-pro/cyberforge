"""One-off: extrait SECTEURS de routers/toolbox.py vers tools/toolbox_sectors.py."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
text = (ROOT / "routers" / "toolbox.py").read_text(encoding="utf-8")
secteurs = re.search(r"^SECTEURS: dict.*?^\}", text, re.M | re.S).group(0)
aliases = re.search(r"^_SECTOR_ALIASES: dict.*?^\}", text, re.M | re.S).group(0)
norm_fn = (
    re.search(r"^def _normalize_sector_key\(.*?^    return raw\n", text, re.M | re.S)
    .group(0)
    .replace("_normalize_sector_key", "normalize_sector_key")
)

header = '''"""Secteurs toolbox — palettes, typos et détection heuristique."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from agents.coremind_agent import ProjectType

'''

detect = '''
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

_PROJECT_TYPE_SECTOR: dict[ProjectType, str] = {
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
    project_type: ProjectType | None = None,
    pricing_category: str | None = None,
) -> str:
    """Détecte le secteur toolbox le plus probable à partir du prompt."""
    if pricing_category and pricing_category in _PRICING_CATEGORY_SECTOR:
        return _PRICING_CATEGORY_SECTOR[pricing_category]

    text = re.sub(r"\\s+", " ", prompt.strip().lower())
    scores: dict[str, int] = {key: 0 for key in SECTEURS}
    for key, keywords in _SECTOR_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[key] = scores.get(key, 0) + len(kw.split()) + 1

    best_key, best_score = max(scores.items(), key=lambda item: item[1])
    if best_score > 0:
        return best_key
    if project_type and project_type in _PROJECT_TYPE_SECTOR:
        return _PROJECT_TYPE_SECTOR[project_type]
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


'''

out = header + secteurs + "\n\n" + aliases + "\n\n\n" + norm_fn + detect
(ROOT / "tools" / "toolbox_sectors.py").write_text(out, encoding="utf-8")
print("written", len(out))

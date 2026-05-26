"""
Extraction de signaux métier depuis le prompt utilisateur + type ArchitectAI.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PromptSeedHints:
    """Indices pour personnaliser les données fictives des templates premium."""

    vertical: str
    brand_name: str
    campaign_names: tuple[str, ...] = ()
    cuisine_label: str = ""
    venue_label: str = ""


_GENERIC_BRANDS = frozenset({"cyberforge", "votre marque", "demo client", "démo client"})


def _clip(text: str, max_len: int = 48) -> str:
    t = re.sub(r"\s+", " ", text.strip())
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip() + "…"


def extract_quoted_names(blob: str) -> list[str]:
    names: list[str] = []
    for m in re.finditer(r"[«\"']([^«\"'\n]{2,50})[»\"']", blob):
        names.append(_clip(m.group(1), 40))
    return names


def extract_campaign_names(blob: str) -> tuple[str, ...]:
    lower = blob.lower()
    found: list[str] = []
    for m in re.finditer(
        r"campagne\s+(?:de\s+)?(?:l['']?)?([A-Za-zÀ-ÿ0-9][\w\s\-–—]{2,42})",
        blob,
        re.IGNORECASE,
    ):
        name = _clip(m.group(1).strip(" -–—"), 42)
        if name and name.lower() not in ("marketing", "été", "hiver"):
            found.append(name)
    for q in extract_quoted_names(blob):
        if any(k in q.lower() for k in ("campagne", "sea", "social", "retail", "luxe", "été")):
            found.append(q)
        elif re.search(r"\b(Q[1-4]|black\s*friday|soldes|rentrée)\b", q, re.I):
            found.append(q)
    # Dédupliquer en gardant l'ordre
    seen: set[str] = set()
    out: list[str] = []
    for name in found:
        key = name.lower()
        if key not in seen:
            seen.add(key)
            out.append(name)
    if not out and ("marketing" in lower or "agence" in lower):
        out = ["Performance SEA Q2", "Social Ads Luxe", "Lead Gen Automne"]
    return tuple(out[:5])


def extract_brand_name(blob: str, *, vertical: str) -> str:
    quoted = extract_quoted_names(blob)
    for q in quoted:
        if not re.search(
            r"\b(campagne|dashboard|crm|landing|démo|demo|application)\b",
            q,
            re.I,
        ):
            return q
    m = re.search(
        r"(?:agence|restaurant|café|cafe|boulangerie|brasserie)\s+([A-Za-zÀ-ÿ][\w\s&'-]{2,32})",
        blob,
        re.I,
    )
    if m:
        return _clip(m.group(1).strip(), 32)
    if vertical == "marketing":
        return "Pulse Agency"
    if vertical == "real_estate":
        return "Habitat Plus"
    if vertical == "restaurant":
        return "La Table du Marché"
    words = re.findall(r"[A-Za-zÀ-ÿ]{3,}", blob)
    if words:
        return _clip(words[0].capitalize(), 28)
    return "Studio Pro"


def extract_cuisine_label(blob: str) -> str:
    lower = blob.lower()
    styles = (
        ("italien", "cuisine italienne"),
        ("japonais", "cuisine japonaise"),
        ("sushi", "bar à sushis"),
        ("gastronomique", "table gastronomique"),
        ("bistrot", "bistrot parisien"),
        ("pizzeria", "pizzeria artisanale"),
        ("boulangerie", "boulangerie-pâtisserie"),
        ("brasserie", "brasserie traditionnelle"),
        ("vegan", "cuisine végétale"),
        ("traiteur", "maison traiteur"),
    )
    for kw, label in styles:
        if kw in lower:
            return label
    if "restaurant" in lower or "café" in lower or "cafe" in lower:
        return "restaurant bistronomique"
    return ""


def extract_venue_label(blob: str) -> str:
    m = re.search(
        r"(?:restaurant|café|cafe|boulangerie|brasserie)\s+([A-Za-zÀ-ÿ][\w\s'-]{2,28})",
        blob,
        re.I,
    )
    if m:
        return _clip(m.group(0), 36)
    if "restaurant" in blob.lower():
        return "restaurant"
    return ""


def build_prompt_seed_hints(prompt: str, *, project_type_label: str = "") -> PromptSeedHints:
    from tools.premium_seed_context import detect_demo_vertical

    blob = f"{project_type_label}\n{prompt}".strip()
    vertical = detect_demo_vertical(blob, project_type_label=project_type_label)
    brand = extract_brand_name(blob, vertical=vertical)
    return PromptSeedHints(
        vertical=vertical,
        brand_name=brand,
        campaign_names=extract_campaign_names(blob) if vertical == "marketing" else (),
        cuisine_label=extract_cuisine_label(blob) if vertical == "restaurant" else "",
        venue_label=extract_venue_label(blob) if vertical == "restaurant" else "",
    )


def is_generic_brand(name: str) -> bool:
    return name.strip().lower() in _GENERIC_BRANDS or "cyberforge" in name.lower()

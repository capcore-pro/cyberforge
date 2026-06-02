"""
Nettoyage des titres de projet dérivés du prompt utilisateur.
"""

from __future__ import annotations

import re

_QUOTE_CHARS = "\"'«»""''`”“”"
_SPLIT_RE = re.compile(
    r"\s*(?:,|;|\||\s+ou\s+|\s+et\s+|\s+avec\s+)\s+",
    re.IGNORECASE,
)
_QUOTED_RE = re.compile(
    r"[«\"']([^»\"']+?)[»\"']|\"([^\"]+)\"|'([^']+)'",
)


def clean_project_title(raw: str, *, max_len: int = 50) -> str:
    """
    Extrait le premier intitulé lisible : premier segment entre guillemets,
    sinon premier segment avant séparateur, sans guillemets parasites.
    """
    text = (raw or "").strip()
    if not text:
        return "Projet sans titre"

    text = text.split("\n", 1)[0].strip()

    chosen: str | None = None
    for match in _QUOTED_RE.finditer(text):
        for group in match.groups():
            if group and group.strip():
                chosen = group.strip()
                break
        if chosen:
            break

    if not chosen:
        parts = _SPLIT_RE.split(text)
        chosen = (parts[0] if parts else text).strip()

    for char in _QUOTE_CHARS:
        chosen = chosen.replace(char, "")
    chosen = re.sub(r"\s+", " ", chosen).strip(" -–—.:?!")

    if not chosen:
        return "Projet sans titre"

    if len(chosen) <= max_len:
        return chosen

    cut = chosen[:max_len].rstrip()
    if len(cut) < len(chosen):
        cut = cut[: max_len - 1].rstrip() + "…"
    return cut


_PREFIX_RE = re.compile(
    r"^(?:description\s*:|projet\s*:|application\s+de\s+gestion\s+pour\s+un?\s*|"
    r"application\s+de\s+gestion\s+|application\s+de|application|site\s+vitrine\s+pour|"
    r"site\s+vitrine|site\s+de|site)\s+",
    re.IGNORECASE,
)


def short_project_name(raw: str, *, max_words: int = 3, max_len: int = 40) -> str:
    """
    Extrait un nom court (≤ max_words) depuis une description.
    Exemples :
      "Application de gestion pour un garage automobile…" -> "Garage Auto"
    """
    base = clean_project_title(raw, max_len=120)
    base = _PREFIX_RE.sub("", base).strip()
    base = re.sub(r"\s+", " ", base).strip(" -–—.:?!")
    if not base:
        return "Projet"

    words = [w for w in base.split(" ") if w]
    short = " ".join(words[:max_words]).strip()
    # capitalisation simple lisible
    short = " ".join(w.capitalize() if len(w) > 2 else w.capitalize() for w in short.split())
    if len(short) > max_len:
        short = short[: max_len - 1].rstrip() + "…"
    return short or "Projet"

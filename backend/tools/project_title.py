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

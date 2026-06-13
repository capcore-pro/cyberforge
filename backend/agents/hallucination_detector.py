"""Détection de contenu générique / placeholder dans le HTML généré."""

from __future__ import annotations

import re
from typing import Any

HALLUCINATION_PATTERNS = [
    r"\[NOM\]",
    r"\[CLIENT\]",
    r"\[VILLE\]",
    r"\[SECTEUR\]",
    r"\[COULEUR\]",
    r"\[VOTRE\s+\w+\]",
    r"\[YOUR\s+\w+\]",
    r"INSERT_\w+_HERE",
    r"PLACEHOLDER",
    r"TODO:",
    r"FIXME:",
    r"lorem ipsum",
    r"exemple\.com",
    r"example\.com",
    r"votre entreprise",
    r"votre nom",
    r"your company name",
    r"acme corp",
    r"test@test\.com",
    r"123 rue example",
    r"à compléter",
    r"à remplir",
    r"coming soon",
    r"under construction",
]


class HallucinationDetector:
    def detect(self, html: str, brief: dict[str, Any]) -> dict[str, Any]:
        issues: list[str] = []
        html_lower = (html or "").lower()

        for pattern in HALLUCINATION_PATTERNS:
            matches = re.findall(pattern, html or "", re.IGNORECASE)
            if matches:
                issues.append(f"Pattern générique: '{matches[0]}'")

        client_name = str(brief.get("client_name") or "").lower()
        if client_name and len(client_name) > 2:
            if client_name not in html_lower:
                issues.append("Nom client absent du HTML")

        couleur = str(brief.get("couleur_primaire") or "")
        if couleur and couleur not in (html or ""):
            issues.append(f"Couleur primaire {couleur} absente")

        score = max(0, 100 - len(issues) * 20)
        severity = (
            "high"
            if len(issues) >= 4
            else "medium"
            if len(issues) >= 2
            else "low"
            if len(issues) >= 1
            else "none"
        )

        return {
            "hallucination_free": len(issues) == 0,
            "score": score,
            "issues": issues,
            "severity": severity,
        }


hallucination_detector = HallucinationDetector()

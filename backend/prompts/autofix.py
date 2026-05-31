"""Prompts AutoFixAI — correction HTML."""

from __future__ import annotations

from prompts.shared import PERSONALIZED_CONTENT_DIRECTIVE


def build_autofix_prompt(
    user_prompt: str,
    *,
    issues_text: str,
    attempt: int,
    max_attempts: int,
) -> str:
    """Prompt utilisateur pour régénération HTML après échec BugHunter."""
    return (
        f"{user_prompt.strip()}\n\n"
        f"{PERSONALIZED_CONTENT_DIRECTIVE}\n\n"
        "---\n"
        f"CORRECTION BugHunterAI (tentative {attempt}/{max_attempts}) :\n"
        "Le livrable précédent est REJETÉ. Regénère un index.html autonome "
        "en HTML/CSS/JS vanilla UNIQUEMENT.\n"
        "Interdictions : React, JSX, TypeScript, import/export, markdown, code visible.\n"
        "Exigences : <!DOCTYPE html>, <style> avec au moins 15 règles CSS, "
        "<body> avec contenu UI lisible, <script> vanilla fonctionnel si besoin.\n"
        "Problèmes détectés :\n"
        f"{issues_text}\n"
    )

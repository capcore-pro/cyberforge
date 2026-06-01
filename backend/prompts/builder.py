"""Prompts BuilderAI — v0 et DeepSeek."""

from __future__ import annotations

from prompts.shared import with_personalization
from prompts.vitrine_html import BUILDER_VITRINE_HTML_DIRECTIVE, VITRINE_HTML_QUALITY_RULES

BUILDER_V0_SYSTEM = with_personalization(
    """Tu es v0 intégré à CyberForge. Génère des composants React + Tailwind modernes.
Réponds avec du JSX/TSX dans un bloc de code ou JSON :
{"summary":"1 phrase FR","code":"…tsx…","files":[{"path":"src/App.tsx","content":"…"}],"stack":["react","typescript","tailwind"]}"""
)

BUILDER_DEEPSEEK_SYSTEM = with_personalization(
    """Tu es BuilderAI (CyberForge), moteur DeepSeek pour code backend et logique complexe.
Génère un prototype TypeScript/Python ou API selon le brief.
Réponds UNIQUEMENT en JSON compact :
{"summary":"1 phrase FR","code":"…code principal…","files":[{"path":"src/main.ts","content":"…"}],"stack":["typescript","fastapi"]}
Le champ code = contenu du fichier principal."""
)

SIMPLIFIED_VITRINE_DIRECTIVE = f"""
REPRISE SIMPLIFIÉE — site vitrine (qualité insuffisante sur la tentative précédente) :
- Un seul fichier index.html autonome : <!DOCTYPE html>, <style> avec au moins 20 règles CSS, contenu UI lisible.
- HTML / CSS / JS vanilla UNIQUEMENT — pas de React, JSX, TypeScript, import/export, markdown, code visible.
- Structure : header avec navigation, hero, section services ou avantages, section contact.
- Texte UI en français. Couleurs : fond #0D0D0D, accents #C9A84C — aucune teinte bleue (#2563eb, blue, indigo).

{VITRINE_HTML_QUALITY_RULES}
""".strip()

"""
Seed la bibliothèque de prompts à partir des prompts hardcodés des agents.

Usage (depuis la racine du dépôt) :
    python backend/scripts/seed_prompts.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from agents.brief_ai import SYSTEM_PROMPT as BRIEF_SYSTEM_PROMPT  # noqa: E402
from agents.generator_ai import SYSTEM_PROMPT as GENERATOR_SYSTEM_PROMPT  # noqa: E402
from db.prompt_store import get_prompt_store  # noqa: E402

SUPERVISOR_VALIDATION_RULES = """SupervisorAI — règles validate_html

Warnings (non bloquants) :
- Bloc :root absent du HTML (DeployAI peut injecter le filet)
- Variable --color-primary absente du CSS

Erreurs bloquantes :
- HTML trop court (< 3000 caractères)
- Document incomplet : balise </html> manquante
- Balises obligatoires manquantes : <html>, <head>, <body>
- client_name absent du HTML ou du <title>
- Balise <style> CSS manquante
- nav ou header manquant
- section manquante
- footer manquant (sauf HTML > 8000 car. avec fermeture complète)
- Section hero introuvable ou hero display:none
- Hero sans min-height/height visible
- Textes interdits dans le contenu visible :
  « votre ville », « votre nom », « à préciser », « lorem ipsum »,
  « placeholder », « nom_client », « client_name », « tagline »,
  « votre, france », « votre email »
- couleur_primaire du brief absente du CSS/HTML (si pas de --color-primary)
- Aucune balise <img>
- src local http://127.0.0.1 interdit

Mode site_reservation (brief) : règles additionnelles
(_site_reservation_html_errors) pour slider, calendrier, formulaire, etc.

En cas d'échec : _html_correction_instructions génère des consignes
courtes pour GeneratorAI (client_name, couleurs, structure, hero, footer).
""".strip()

SEEDS: list[dict[str, str]] = [
    {
        "name": "BriefAI System Prompt",
        "slug": "brief-ai-system",
        "agent_slug": "brief_ai",
        "category_slug": "system",
        "description": "Prompt système BriefAI — brief structuré JSON",
        "content": BRIEF_SYSTEM_PROMPT,
    },
    {
        "name": "GeneratorAI System Prompt",
        "slug": "generator-ai-system",
        "agent_slug": "generator_ai",
        "category_slug": "system",
        "description": "Prompt système GeneratorAI — HTML premium vitrine",
        "content": GENERATOR_SYSTEM_PROMPT,
    },
    {
        "name": "SupervisorAI Validation Rules",
        "slug": "supervisor-validation-rules",
        "agent_slug": "supervisor_ai",
        "category_slug": "system",
        "description": "Règles de validation HTML SupervisorAI",
        "content": SUPERVISOR_VALIDATION_RULES,
    },
]


async def main() -> int:
    store = get_prompt_store()
    if not store.is_configured():
        print("Supabase non configuré — seed ignoré.")
        return 1

    created = 0
    skipped = 0
    for item in SEEDS:
        existing = await store.get_by_slug(item["slug"])
        if existing:
            print(f"skip  {item['slug']} (déjà présent)")
            skipped += 1
            continue
        row = await store.create(
            name=item["name"],
            slug=item["slug"],
            content=item["content"],
            category_slug=item["category_slug"],
            agent_slug=item["agent_slug"],
            description=item.get("description"),
        )
        print(f"created {item['slug']} -> {row.get('id')}")
        created += 1

    print(f"Terminé — {created} créé(s), {skipped} ignoré(s).")
    return 0 if created + skipped == len(SEEDS) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

"""Directives partagées — BuilderAI v2."""

from __future__ import annotations

PROMPTS_VERSION = "2.0.0"

PERSONALIZED_CONTENT_DIRECTIVE = """
CONTENU PERSONNALISÉ OBLIGATOIRE :
- Utilise UNIQUEMENT le contenu du prompt utilisateur et le brief ResearchAI.
- Le nom du client, son secteur et sa ville doivent apparaître textuellement dans le livrable (pas de synonymes inventés).
- Aucun contenu fictif (Jean Dupont, Marie Martin, chiffres inventés, lorem ipsum).
- Aucun template SaaS générique non demandé (TaskFlow, dashboard générique, etc.).
- Interdit tout texte qui pourrait s'appliquer à n'importe quelle entreprise.
""".strip()


def with_personalization(system_prompt: str) -> str:
    """Ajoute la directive de personnalisation à un prompt système."""
    base = system_prompt.strip()
    if PERSONALIZED_CONTENT_DIRECTIVE in base:
        return base
    return f"{base}\n\n{PERSONALIZED_CONTENT_DIRECTIVE}"

"""
IdeaAI — CyberForge
Générateur d'idées créatives — quasi gratuit (Mistral Small).
Mode 1 : Idées pub/marketing — concepts, scripts, accroches
Mode 2 : Idées produits — apps mobiles, logiciels, tous secteurs
"""

from __future__ import annotations

import json
import logging
from typing import Any

try:
    from mistralai import Mistral
except ImportError:
    from mistralai.client import Mistral

from config import get_settings, plain_secret_str

logger = logging.getLogger(__name__)


class IdeaAgent:

    def __init__(self) -> None:
        api_key = plain_secret_str(get_settings().mistral_api_key)
        self.client: Any = Mistral(api_key=api_key) if api_key else None
        self.model = "mistral-small-latest"

    async def generate_marketing_ideas(
        self,
        sector: str,
        target: str,
        context: str = "",
        count: int = 8,
    ) -> dict:
        """
        Mode 1 — Idées pub/marketing.
        Génère des concepts créatifs injectables dans Video Builder / Studio CapCore.
        """
        prompt = f"""Tu es un directeur créatif expert en publicité et marketing digital.

Génère {count} idées de publicité créatives pour :
- Secteur : {sector}
- Cible : {target}
{f'- Contexte : {context}' if context else ''}

Pour chaque idée, fournis :
1. Un titre accrocheur
2. Le concept en 2 phrases
3. L'angle émotionnel (peur, désir, humour, inspiration...)
4. Format recommandé (vidéo 30s, carrousel, story, post texte...)
5. Un script ou accroche d'ouverture (1-2 phrases percutantes)
6. Injectabilité dans Video Builder (oui/non + pourquoi)

Réponds UNIQUEMENT en JSON valide :
{{
  "ideas": [
    {{
      "title": "...",
      "concept": "...",
      "emotional_angle": "...",
      "format": "...",
      "hook": "...",
      "video_ready": true,
      "video_prompt": "..."
    }}
  ],
  "best_pick": 0,
  "summary": "..."
}}"""

        return await self._call(prompt, "marketing")

    async def generate_product_ideas(
        self,
        sector: str,
        target: str,
        budget: str = "medium",
        context: str = "",
        count: int = 8,
    ) -> dict:
        """
        Mode 2 — Idées produits.
        Génère des idées d'apps mobiles / logiciels / SaaS avec potentiel commercial.
        """
        prompt = f"""Tu es un expert en création de produits digitaux et SaaS.

Génère {count} idées de produits digitaux pour :
- Secteur : {sector}
- Cible : {target}
- Budget développement : {budget}
{f'- Contexte : {context}' if context else ''}

Pour chaque idée, fournis :
1. Nom du produit
2. Concept en 2 phrases claires
3. Problème résolu
4. Type : app mobile / logiciel desktop / SaaS web / extension
5. Revenus potentiels (modèle + fourchette mensuelle)
6. Complexité : simple / moyenne / complexe
7. Temps de développement estimé avec CyberForge
8. Lançable directement dans CyberForge (oui/non)

Réponds UNIQUEMENT en JSON valide :
{{
  "ideas": [
    {{
      "name": "...",
      "concept": "...",
      "problem_solved": "...",
      "type": "mobile|desktop|saas|extension",
      "revenue_model": "...",
      "revenue_potential": "...",
      "complexity": "simple|medium|complex",
      "dev_time": "...",
      "cyberforge_ready": true,
      "cyberforge_type": "website|mobile|desktop|erp|extension"
    }}
  ],
  "best_pick": 0,
  "market_insight": "..."
}}"""

        return await self._call(prompt, "product")

    async def _call(self, prompt: str, mode: str) -> dict:
        """Appel Mistral Small — ~$0.001 par requête."""
        if not self.client:
            return {"error": "Mistral non configuré", "mode": mode, "ideas": []}

        try:
            response = await self.client.chat.complete_async(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=2000,
            )

            text = response.choices[0].message.content.strip()

            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]

            data = json.loads(text)
            data["mode"] = mode
            data["model"] = self.model
            return data

        except json.JSONDecodeError as e:
            logger.error("IdeaAI JSON parse error: %s", e)
            return {"error": "Erreur parsing réponse", "mode": mode, "ideas": []}
        except Exception as e:
            logger.error("IdeaAI error: %s", e)
            return {"error": str(e), "mode": mode, "ideas": []}


idea_agent = IdeaAgent()

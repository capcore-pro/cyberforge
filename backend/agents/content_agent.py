"""
ContentAI — Génération contenu réseaux sociaux
Mistral Small — ~$0.001/req
Formats : LinkedIn / Instagram / TikTok / Twitter
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

try:
    from mistralai import Mistral
except ImportError:
    from mistralai.client import Mistral

from config import get_settings, plain_secret_str

logger = logging.getLogger(__name__)

FORMATS = {
    "linkedin": {
        "label": "LinkedIn",
        "ton": "professionnel et inspirant",
        "longueur": "150-300 mots",
        "style": "storytelling business, emojis modérés, appel à l'action final",
    },
    "instagram": {
        "label": "Instagram",
        "ton": "authentique et visuel",
        "longueur": "80-150 mots",
        "style": "phrases courtes, emojis expressifs, appel à l'action, hashtags en fin",
    },
    "tiktok": {
        "label": "TikTok",
        "ton": "dynamique et accrocheur",
        "longueur": "50-100 mots",
        "style": "phrase d'accroche forte, rythme rapide, call-to-action direct",
    },
    "twitter": {
        "label": "Twitter / X",
        "ton": "percutant et direct",
        "longueur": "max 280 caractères",
        "style": "message clé en une phrase, 1-2 hashtags max",
    },
}

SECTEURS = [
    "Artisan / Métier manuel",
    "Restaurant / Food",
    "Commerce local",
    "Consultant / Coach",
    "E-commerce",
    "Immobilier",
    "Santé / Bien-être",
    "Tech / SaaS",
    "Association",
    "Autre",
]

CAPCORE_SUBJECTS = [
    {"key": "nouvelle_fonctionnalite", "label": "Nouvelle fonctionnalité CyberForge"},
    {"key": "offre_du_moment", "label": "Offre du moment"},
    {"key": "temoignage_client", "label": "Témoignage client"},
    {"key": "presentation_service", "label": "Présentation service"},
    {"key": "conseil_digital", "label": "Conseil digital gratuit"},
    {"key": "behind_the_scenes", "label": "Dans les coulisses CapCore"},
]

CAPCORE_TONE = """
Tu es Mat, fondateur de CapCore Studio Digital.
Ton entreprise : CapCore Studio Digital.
Ton produit phare : CyberForge — une plateforme IA qui génère automatiquement des sites web, applications mobiles, logiciels desktop, ERPs et contenus marketing pour les artisans et PME françaises.
Ton ton : direct, expert, humain, sans jargon inutile. Tu parles en ton propre nom (je/nous).
Tu t'adresses à des artisans, commerçants, TPE/PME qui veulent se digitaliser sans se ruiner.
Ne mentionne jamais de prix. Ne fais pas de fausses promesses. Sois authentique.
"""

CAROUSEL_TEXTS_PROMPT = """Tu es expert en marketing digital pour artisans et PME françaises.
Génère les textes pour un carrousel publicitaire de 5 slides sur le sujet : {sujet_label}

Contexte : CapCore Studio Digital — agence digitale IA pour artisans et PME françaises.

Retourne UNIQUEMENT ce JSON valide, sans markdown, sans explication :
{{
  "slides": [
    {{"role": "accroche", "titre": "...", "sous_texte": "..."}},
    {{"role": "argument_1", "titre": "...", "sous_texte": "..."}},
    {{"role": "argument_2", "titre": "...", "sous_texte": "..."}},
    {{"role": "demonstration", "titre": "...", "sous_texte": "..."}},
    {{"role": "cta", "titre": "...", "sous_texte": "..."}}
  ]
}}

Règles strictes :
- titre : 4 à 7 mots, impactant
- sous_texte : 8 à 12 mots, bénéfice concret
- Tout en français
- Ton : direct, expert, humain
- Slide cta : sous_texte = "Contactez-nous pour démarrer votre projet digital"
"""


class ContentAgent:
    def __init__(self) -> None:
        api_key = plain_secret_str(get_settings().mistral_api_key)
        self.client: Any = Mistral(api_key=api_key) if api_key else None
        self.model = "mistral-small-latest"

    async def _call(self, prompt: str) -> str:
        if not self.client:
            raise RuntimeError("Mistral non configuré")

        response = await self.client.chat.complete_async(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.85,
            max_tokens=1500,
        )
        return response.choices[0].message.content.strip()

    async def generate_free_text(
        self,
        text_type: str,
        sujet: str,
        contexte: str = "",
    ) -> str:
        """Texte court pour champs Studio Builder (titre, slogan, service, etc.)."""
        TYPE_PROMPTS = {
            "description": "Génère une description professionnelle courte (2-3 phrases)",
            "presentation": "Génère une présentation complète (5-6 phrases)",
            "titre": "Génère un titre accrocheur (max 8 mots)",
            "slogan": "Génère un slogan percutant (max 12 mots)",
            "service": "Génère une description de service (1-2 phrases, bénéfice client)",
            "temoignage": "Génère un témoignage client authentique (2-3 phrases)",
            "faq_question": "Génère une question FAQ pertinente",
            "faq_reponse": "Génère une réponse FAQ claire et rassurante (2-3 phrases)",
            "cta": "Génère un texte de bouton CTA court et engageant (2-5 mots)",
        }
        instruction = TYPE_PROMPTS.get(
            text_type,
            "Génère un texte professionnel court",
        )

        user_prompt = f"{instruction}\nSujet : {sujet.strip()}"
        if contexte.strip():
            user_prompt += f"\nContexte : {contexte.strip()}"
        if not sujet.strip() and not contexte.strip():
            raise ValueError("Sujet ou contexte requis")

        raw = await self._call_mistral(
            system_prompt=(
                "Tu es expert en communication digitale pour artisans "
                "et PME françaises. Réponds uniquement avec le texte demandé, "
                "sans introduction ni commentaire."
            ),
            user_prompt=user_prompt,
            max_tokens=300,
        )
        return raw.strip().strip('"').strip("'")

    async def _call_mistral(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1500,
    ) -> str:
        if not self.client:
            raise RuntimeError("Mistral non configuré")

        response = await self.client.chat.complete_async(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.85,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()

    def _parse_json(self, raw: str) -> dict | list:
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
        return json.loads(cleaned)

    async def generate_post(
        self,
        sujet: str,
        secteur: str,
        format_reseau: str,
        ton_personnalise: str = "",
        nom_entreprise: str = "",
    ) -> dict:
        """Génère un post pour un réseau social donné."""
        fmt = FORMATS.get(format_reseau, FORMATS["linkedin"])
        ton = ton_personnalise or fmt["ton"]
        entreprise = f"pour l'entreprise « {nom_entreprise} »" if nom_entreprise else ""

        prompt = f"""Tu es un expert en marketing digital et copywriting pour les PME françaises.

Génère un post {fmt['label']} {entreprise} sur le sujet suivant :
Sujet : {sujet}
Secteur : {secteur}
Ton : {ton}
Longueur : {fmt['longueur']}
Style : {fmt['style']}

Réponds UNIQUEMENT en JSON valide, sans markdown, avec exactement ces clés :
{{
  "post": "le texte complet du post prêt à publier",
  "accroche": "la première phrase d'accroche seule",
  "conseil": "un conseil d'optimisation pour ce post (1 phrase)"
}}"""

        try:
            raw = await self._call(prompt)
            result = self._parse_json(raw)
            if not isinstance(result, dict):
                raise ValueError("Réponse JSON invalide")
            return {
                "post": result.get("post", ""),
                "accroche": result.get("accroche", ""),
                "conseil": result.get("conseil", ""),
                "format": format_reseau,
                "label": fmt["label"],
            }
        except json.JSONDecodeError as e:
            logger.error("ContentAI JSON parse error (post): %s", e)
            return {"error": "Erreur parsing réponse", "format": format_reseau}
        except Exception as e:
            logger.error("ContentAI error (post): %s", e)
            return {"error": str(e), "format": format_reseau}

    async def generate_hashtags(
        self,
        sujet: str,
        secteur: str,
        format_reseau: str,
        nb_hashtags: int = 10,
    ) -> dict:
        """Génère une liste de hashtags optimisés."""
        prompt = f"""Tu es un expert SEO réseaux sociaux pour les PME françaises.

Génère {nb_hashtags} hashtags optimisés pour {format_reseau.capitalize()} sur :
Sujet : {sujet}
Secteur : {secteur}

Mélange :
- 3 hashtags très populaires (>500k posts)
- 4 hashtags moyens (50k-500k posts)
- 3 hashtags de niche (<50k posts, très ciblés)

Réponds UNIQUEMENT en JSON valide, sans markdown :
{{
  "hashtags": ["#hashtag1", "#hashtag2", ...],
  "conseil": "conseil d'utilisation en 1 phrase"
}}"""

        try:
            raw = await self._call(prompt)
            result = self._parse_json(raw)
            if not isinstance(result, dict):
                raise ValueError("Réponse JSON invalide")
            return {
                "hashtags": result.get("hashtags", []),
                "conseil": result.get("conseil", ""),
            }
        except json.JSONDecodeError as e:
            logger.error("ContentAI JSON parse error (hashtags): %s", e)
            return {"error": "Erreur parsing réponse", "hashtags": []}
        except Exception as e:
            logger.error("ContentAI error (hashtags): %s", e)
            return {"error": str(e), "hashtags": []}

    async def generate_bio(
        self,
        nom_entreprise: str,
        secteur: str,
        valeur_ajoutee: str,
        format_reseau: str,
    ) -> dict:
        """Génère une bio de profil réseau social."""
        limites = {
            "linkedin": "300 caractères max",
            "instagram": "150 caractères max",
            "tiktok": "80 caractères max",
            "twitter": "160 caractères max",
        }
        limite = limites.get(format_reseau, "150 caractères max")

        prompt = f"""Tu es expert en personal branding pour les PME françaises.

Génère 3 versions de bio {format_reseau.capitalize()} pour :
Entreprise : {nom_entreprise}
Secteur : {secteur}
Valeur ajoutée : {valeur_ajoutee}
Limite : {limite}

Réponds UNIQUEMENT en JSON valide, sans markdown :
{{
  "bios": [
    {{"version": "Directe", "texte": "..."}},
    {{"version": "Storytelling", "texte": "..."}},
    {{"version": "Avec emojis", "texte": "..."}}
  ]
}}"""

        try:
            raw = await self._call(prompt)
            result = self._parse_json(raw)
            if not isinstance(result, dict):
                raise ValueError("Réponse JSON invalide")
            return {
                "bios": result.get("bios", []),
                "format": format_reseau,
                "limite": limite,
            }
        except json.JSONDecodeError as e:
            logger.error("ContentAI JSON parse error (bio): %s", e)
            return {"error": "Erreur parsing réponse", "bios": [], "format": format_reseau}
        except Exception as e:
            logger.error("ContentAI error (bio): %s", e)
            return {"error": str(e), "bios": [], "format": format_reseau}

    def get_capcore_subjects(self) -> list:
        return CAPCORE_SUBJECTS

    async def generate_capcore_post(
        self,
        sujet_type: str,
        format_reseau: str,
        angle: str = "",
    ) -> dict:
        sujet_label = next(
            (s["label"] for s in CAPCORE_SUBJECTS if s["key"] == sujet_type),
            sujet_type,
        )
        format_info = FORMATS.get(format_reseau, FORMATS["linkedin"])
        angle_text = f"\nAngle particulier à exploiter : {angle}" if angle else ""

        prompt = f"""
{CAPCORE_TONE}

Génère un post {format_reseau} sur le sujet : "{sujet_label}".
Format cible : {format_info['label']} — ton : {format_info['ton']} — longueur : {format_info['longueur']}.{angle_text}

Réponds UNIQUEMENT en JSON valide, sans markdown, sans texte avant ou après :
{{
  "post": "le post complet prêt à publier",
  "accroche": "première phrase percutante (accroche seule)",
  "conseil": "conseil pro sur ce type de contenu pour ce réseau",
  "hashtags": ["hashtag1", "hashtag2", "hashtag3", "hashtag4", "hashtag5"]
}}
"""
        try:
            raw = await self._call(prompt)
            result = self._parse_json(raw)
            return {**result, "format": format_reseau, "sujet": sujet_label}
        except Exception as e:
            return {"error": str(e), "format": format_reseau, "hashtags": []}

    async def generate_carousel_texts(self, sujet_label: str) -> list[dict]:
        """Génère les 5 titres + sous-textes pour un carrousel via Mistral Small."""
        prompt = CAROUSEL_TEXTS_PROMPT.format(sujet_label=sujet_label)
        raw = await self._call_mistral(
            system_prompt="Tu es expert en marketing digital. Réponds uniquement en JSON valide.",
            user_prompt=prompt,
            max_tokens=600,
        )
        data = self._parse_json(raw)
        if not isinstance(data, dict):
            raise ValueError("Réponse JSON invalide")
        slides = data.get("slides", [])
        if not isinstance(slides, list):
            raise ValueError("Réponse JSON invalide — slides manquant")
        if len(slides) != 5:
            raise ValueError(f"5 slides attendues, {len(slides)} reçues")
        return slides

    def get_formats(self) -> list:
        return [
            {"id": k, "label": v["label"], "ton": v["ton"], "longueur": v["longueur"]}
            for k, v in FORMATS.items()
        ]

    def get_secteurs(self) -> list:
        return SECTEURS


content_agent = ContentAgent()

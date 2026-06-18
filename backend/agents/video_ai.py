# ============================================
# VIDEO AI — CyberForge
# Agent IA génération prompts cinématiques
# Modèle : Claude Sonnet (INTOUCHABLE)
# ============================================

import os
import json
import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """Tu es VideoAI, expert mondial en direction cinématique et publicités premium.

Tu reçois : marque + brief produit + ambiance souhaitée.

Tu génères exactement 6 scènes vidéo cinématiques cohérentes.

FORMAT DE RÉPONSE — JSON uniquement, aucun texte autour :
{
  "concept": "Concept global de la pub en 1 phrase",
  "color_palette": "Description palette couleurs cohérente",
  "scenes": [
    {
      "scene_number": 1,
      "title": "Titre court de la scène",
      "description_fr": "Description en français de ce que l'on voit (2-3 phrases simples)",
      "prompt": "Prompt Kling optimisé 50-80 mots en anglais",
      "camera_move": "slow dolly forward",
      "mood": "opening",
      "duration": 5
    }
  ]
}

Pour chaque scène, génère AUSSI :
- "description_fr" : description en français de ce que l'on voit dans la scène (2-3 phrases simples, vocabulaire accessible)
- "prompt" : prompt Kling en anglais (inchangé, 50-80 mots)

RÈGLES PROMPTS KLING :
- Toujours commencer par le mouvement de caméra
- Cinematic lighting obligatoire
- Ultra realistic, 8K quality
- Pas de texte ni logo dans les vidéos
- Couleurs cohérentes entre toutes les scènes
- Progression dramatique : opening → build → climax → reveal
- La progression narrative doit refléter le message clé fourni dans le brief
- La scène 6 (reveal) doit TOUJOURS intégrer visuellement le call to action dans sa description

RÈGLES PROMPTS VISUELS CONCRETS :
- Toujours décrire UN sujet principal visible (une personne, un objet, un lieu précis)
- Exemples de sujets concrets :
  * "a developer typing on a keyboard"
  * "a smartphone screen displaying a website"
  * "a business owner looking at analytics dashboard"
  * "hands typing on a laptop in a dark office"
  * "a website loading and appearing on screen"
- Éviter les concepts abstraits comme :
  * "digital void" / "cyber space" / "data streams"
  * "holographic interface" / "neural network sphere"
- Toujours inclure l'environnement :
  * "in a modern dark office"
  * "on a sleek desk with monitors"
  * "in front of multiple screens"
- Toujours inclure l'action :
  * "typing rapidly" / "clicking" / "scrolling"
  * "presenting to a client" / "reviewing designs"
- Les prompts anglais (prompt) doivent appliquer ces règles : sujet + lieu + action visibles
- Les description_fr doivent décrire la même scène concrète en langage simple

MOUVEMENTS DE CAMÉRA DISPONIBLES :
slow dolly forward, slow dolly backward, pan left, pan right,
crane up, crane down, static shot, slow zoom in, slow zoom out,
orbital shot, handheld subtle

MOODS SÉQUENCE :
scene 1 → opening
scene 2 → build
scene 3 → tension
scene 4 → climax
scene 5 → resolution
scene 6 → reveal

PALETTES PAR MARQUE :
cyberforge → deep black, electric cyan, golden accents
capcopy → dark navy, white, electric blue
lumio → soft white, warm gold, sage green
vocali → deep purple, magenta, silver

Réponds UNIQUEMENT en JSON valide. Zéro texte avant ou après."""


BRAND_CONTEXTS = {
    "cyberforge": """CyberForge est une usine logicielle IA qui génère des sites web, apps et logiciels en quelques minutes.
ÉLÉMENTS VISUELS : développeur devant des écrans générant du code, interface sombre avec des éléments cyan, sites web qui apparaissent magiquement, tableau de bord IA avec métriques, clavier mécanique avec éclairage cyan.""",
    "capcopy": """Cap Copy est une agence de copywriting IA premium.
ÉLÉMENTS VISUELS : rédacteur devant un MacBook, textes qui s'écrivent automatiquement, clients satisfaits lisant des propositions, bureau élégant avec livres et plantes.""",
    "lumio": """Lumio est une application d'apprentissage IA.
ÉLÉMENTS VISUELS : étudiant souriant avec tablette, flashcards qui apparaissent à l'écran, graphiques de progression, bibliothèque lumineuse.""",
    "vocali": """Vocali est une plateforme de voix IA ultra-réaliste.
ÉLÉMENTS VISUELS : microphone professionnel, ondes sonores visualisées, studio d'enregistrement, personne parlant avec des sous-titres qui apparaissent en temps réel.""",
}


class VideoAI:

    async def generate_scenes(
        self,
        brand: str,
        brief: str,
        ambiance: str = "cinématique premium",
        slogan: str = "",
        key_message: str = "",
        call_to_action: str = "",
    ) -> dict:
        """Génère 6 scènes cinématiques via Claude Sonnet."""

        brand_context = BRAND_CONTEXTS.get(brand, BRAND_CONTEXTS["cyberforge"])

        user_prompt = f"""Marque : {brand.upper()}
Contexte : {brand_context}
Brief : {brief}
Slogan : {slogan or "À définir"}
Message clé : {key_message or "À définir"}
Call to action : {call_to_action or "À définir"}
Ambiance : {ambiance}

Génère 6 scènes cinématiques premium."""

        logger.info(f"VideoAI generating scenes for {brand}...")

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": MODEL,
                    "max_tokens": 3000,
                    "system": SYSTEM_PROMPT,
                    "messages": [
                        {"role": "user", "content": user_prompt}
                    ]
                }
            )

        data = response.json()

        if "error" in data:
            raise Exception(f"Anthropic error: {data['error']['message']}")

        raw = data["content"][0]["text"].strip()

        # Nettoyage JSON
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        scenes_data = json.loads(raw)

        logger.info(f"VideoAI generated {len(scenes_data['scenes'])} scenes")
        return scenes_data

    async def refine_scene(
        self,
        scene: dict,
        instruction: str
    ) -> dict:
        """Affine un prompt de scène selon instruction utilisateur."""

        user_prompt = f"""Scène actuelle :
Titre : {scene.get('title', '')}
Description (fr) : {scene.get('description_fr', '')}
Prompt (en) : {scene.get('prompt', '')}
Caméra : {scene.get('camera_move', '')}

Instruction en français : {instruction}
Modifie le prompt anglais ET génère une nouvelle description_fr en français correspondante.

Retourne uniquement la scène modifiée en JSON avec les champs :
scene_number, title, description_fr, prompt, camera_move, mood, duration."""

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": MODEL,
                    "max_tokens": 500,
                    "system": (
                        "Tu es VideoAI. L'instruction utilisateur est en français. "
                        "Réponds uniquement en JSON valide avec description_fr (français) "
                        "et prompt (anglais Kling)."
                    ),
                    "messages": [
                        {"role": "user", "content": user_prompt}
                    ]
                }
            )

        data = response.json()
        raw = data["content"][0]["text"].strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        return json.loads(raw.strip())


# Instance globale
video_ai = VideoAI()

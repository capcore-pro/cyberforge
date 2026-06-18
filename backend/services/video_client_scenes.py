"""
Descriptions françaises pour scènes vidéo client (prompts sectoriels EN).
"""

from __future__ import annotations

import json
import logging
import re

from llm.mistral_client import mistral_client

logger = logging.getLogger(__name__)

_DESCRIPTIONS_SYSTEM = """Tu es rédacteur vidéo pour clients non techniques.
On te donne des prompts cinématiques en anglais (pour un moteur vidéo IA).

Pour CHAQUE prompt, écris une description_fr en français simple (1 à 2 phrases) :
- Décris ce que le client VERRA à l'écran (sujet, lieu, action, ambiance).
- Vocabulaire accessible, pas de jargon technique.
- Interdit : Kling, 4K, shallow depth of field, bokeh, dolly, crane, macro lens, etc.

Réponds UNIQUEMENT en JSON valide, sans markdown :
{{"descriptions": ["description scène 1", "description scène 2", ...]}}

Le tableau "descriptions" doit contenir exactement {count} chaîne(s), dans le même ordre que les prompts."""

_TECH_TERMS = re.compile(
    r"\b(?:4k|8k|ultra\s+sharp|shallow\s+depth\s+of\s+field|bokeh|"
    r"cinematic|macro\s+lens|tracking\s+shot|dolly|crane|aerial\s+drone|"
    r"slow\s+motion|golden\s+hour)\b",
    re.IGNORECASE,
)


def _parse_json_object(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```", 1)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0]
    return json.loads(text.strip())


def _fallback_description_fr(prompt_en: str) -> str:
    simplified = _TECH_TERMS.sub("", prompt_en)
    simplified = re.sub(r"\s*—\s*Style:.*$", "", simplified, flags=re.IGNORECASE)
    simplified = re.sub(r"\s+", " ", simplified).strip(" ,.")
    if len(simplified) > 220:
        simplified = simplified[:217].rsplit(" ", 1)[0] + "..."
    return f"À l'écran : {simplified}." if simplified else "Scène à valider avec le client."


async def generate_french_descriptions(
    prompts_en: list[str],
    *,
    secteur: str = "",
) -> list[str]:
    """Génère une description_fr par prompt anglais (Mistral Small, fallback local)."""
    if not prompts_en:
        return []

    if mistral_client.is_configured():
        try:
            return await _mistral_descriptions(prompts_en, secteur=secteur)
        except Exception as exc:
            logger.warning("Mistral descriptions échouées, fallback: %s", exc)

    return [_fallback_description_fr(prompt) for prompt in prompts_en]


async def _mistral_descriptions(prompts_en: list[str], *, secteur: str) -> list[str]:
    count = len(prompts_en)
    user_payload = json.dumps(
        {"secteur": secteur or "général", "prompts": prompts_en},
        ensure_ascii=False,
    )
    text, _usage = await mistral_client.complete_small(
        [{"role": "user", "content": user_payload}],
        max_tokens=max(800, count * 180),
        temperature=0.35,
        system_prompt=_DESCRIPTIONS_SYSTEM.format(count=count),
    )
    parsed = _parse_json_object(text)
    descriptions = parsed.get("descriptions")
    if not isinstance(descriptions, list) or len(descriptions) != count:
        raise ValueError(
            f"Réponse Mistral invalide: {len(descriptions) if isinstance(descriptions, list) else 0} "
            f"descriptions pour {count} prompts"
        )
    return [str(item).strip() for item in descriptions]


def build_client_scene_objects(
    prompts_en: list[str],
    descriptions_fr: list[str],
) -> list[dict]:
    return [
        {
            "description_fr": descriptions_fr[i],
            "prompt_en": prompts_en[i],
        }
        for i in range(len(prompts_en))
    ]

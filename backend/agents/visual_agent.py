from __future__ import annotations

import asyncio
from typing import Any

import httpx

from config import get_settings, plain_secret_str

REPLICATE_API_BASE = "https://api.replicate.com/v1"

FLUX_MODEL_AVATAR = "black-forest-labs/flux-1.1-pro"
FLUX_MODEL_VERSION = None  # flux-1.1-pro utilise l'endpoint /models/{owner}/{name}/predictions

VISUAL_FORMATS = {
    "9:16": {
        "label": "Stories / TikTok",
        "width": 768,
        "height": 1344,
        "usage": "TikTok, Instagram Stories, Reels",
    },
    "1:1": {
        "label": "Instagram Feed",
        "width": 1024,
        "height": 1024,
        "usage": "Instagram Feed, Facebook",
    },
    "1:1_facebook": {
        "label": "Facebook Post",
        "width": 1024,
        "height": 1024,
        "usage": "Facebook Post, Facebook Story",
    },
    "16:9": {
        "label": "LinkedIn / YouTube",
        "width": 1344,
        "height": 768,
        "usage": "LinkedIn, YouTube thumbnail",
    },
}

AVATAR_POSES = [
    {
        "key": "presentation",
        "label": "Présentation",
        "description": "arms open, welcoming gesture, friendly smile",
    },
    {
        "key": "explication",
        "label": "Explication",
        "description": "pointing finger up, explaining gesture, engaged expression",
    },
    {
        "key": "cta",
        "label": "Appel à l'action",
        "description": "thumbs up, confident look directly at camera",
    },
    {
        "key": "celebration",
        "label": "Célébration",
        "description": "victory pose, arms raised, big smile",
    },
    {
        "key": "working",
        "label": "Derrière l'ordi",
        "description": "sitting at desk, hands on keyboard, focused on screen",
    },
    {
        "key": "showing",
        "label": "Montrant un site",
        "description": "holding tablet showing a website, presenting screen to camera",
    },
]

CAPCORE_AVATAR_BASE_PROMPT = """3D Pixar-style cartoon character, male founder, 
short dark hair, full dark beard, strong jawline, brown eyes, 
confident professional expression, wearing dark tech jacket,
high quality 3D render, cinematic lighting, sharp details,
professional digital art, octane render style"""

CAPCORE_BACKGROUND = """dark background #0f0f13, 
subtle cyan accent lighting #00d4ff, 
tech atmosphere, depth of field"""


class VisualAgent:
    def __init__(self) -> None:
        self._api_key: str | None = None
        try:
            self._api_key = plain_secret_str(get_settings().replicate_api_key)
        except Exception:
            self._api_key = None

    @property
    def _configured(self) -> bool:
        return bool(self._api_key)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Prefer": "wait=60",
        }

    def get_formats(self) -> list:
        return [
            {"key": k, **v} for k, v in VISUAL_FORMATS.items()
        ]

    def get_avatar_poses(self) -> list:
        return AVATAR_POSES

    def _extract_output_url(self, output: Any) -> str | None:
        if isinstance(output, str) and output.startswith("http"):
            return output
        if isinstance(output, list) and output:
            first = output[0]
            if isinstance(first, str) and first.startswith("http"):
                return first
        if isinstance(output, dict):
            for key in ("url", "image", "output"):
                val = output.get(key)
                if isinstance(val, str) and val.startswith("http"):
                    return val
        return None

    async def _call_replicate(
        self,
        prompt: str,
        width: int,
        height: int,
        timeout: float = 120.0,
    ) -> str:
        if not self._configured:
            raise RuntimeError("Replicate non configuré — REPLICATE_API_KEY manquant")

        owner, name = FLUX_MODEL_AVATAR.split("/")
        create_url = f"{REPLICATE_API_BASE}/models/{owner}/{name}/predictions"

        input_payload = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "num_inference_steps": 28,
            "guidance": 3.5,
            "output_format": "png",
            "output_quality": 95,
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                create_url,
                json={"input": input_payload},
                headers=self._headers(),
            )
            resp.raise_for_status()
            payload = resp.json()

            status = payload.get("status")
            if status == "succeeded":
                url = self._extract_output_url(payload.get("output"))
                if url:
                    return url
                raise RuntimeError("Replicate succeeded mais output vide")

            if status == "failed":
                raise RuntimeError(f"Replicate failed: {payload.get('error')}")

            # Polling si pas encore terminé
            prediction_id = payload.get("id")
            if not prediction_id:
                raise RuntimeError("Replicate — pas de prediction_id dans la réponse")

            poll_url = f"{REPLICATE_API_BASE}/predictions/{prediction_id}"
            poll_headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            }
            max_polls = 20
            for _ in range(max_polls):
                await asyncio.sleep(5)
                poll_resp = await client.get(poll_url, headers=poll_headers)
                poll_resp.raise_for_status()
                poll_data = poll_resp.json()
                poll_status = poll_data.get("status")

                if poll_status == "succeeded":
                    url = self._extract_output_url(poll_data.get("output"))
                    if url:
                        return url
                    raise RuntimeError("Replicate succeeded mais output vide")

                if poll_status == "failed":
                    raise RuntimeError(f"Replicate failed: {poll_data.get('error')}")

        raise RuntimeError("Replicate timeout — aucune réponse après polling")

    async def generate_avatar_pose(
        self,
        pose_key: str,
        format_key: str = "1:1",
    ) -> dict:
        pose = next(
            (p for p in AVATAR_POSES if p["key"] == pose_key),
            None,
        )
        if not pose:
            return {"error": f"Pose inconnue : {pose_key}"}

        fmt = VISUAL_FORMATS.get(format_key, VISUAL_FORMATS["1:1"])

        prompt = (
            f"{CAPCORE_AVATAR_BASE_PROMPT}, "
            f"{pose['description']}, "
            f"{CAPCORE_BACKGROUND}, "
            f"full body or half body shot, clean composition, no text, "
            f"{'portrait' if format_key in ('1:1', '1:1_facebook') else 'vertical composition' if format_key == '9:16' else 'horizontal composition'}"
        )

        try:
            image_url = await self._call_replicate(
                prompt=prompt,
                width=fmt["width"],
                height=fmt["height"],
            )
            return {
                "image_url": image_url,
                "pose_key": pose_key,
                "pose_label": pose["label"],
                "format": format_key,
                "prompt_used": prompt,
            }
        except Exception as e:
            return {"error": str(e), "pose_key": pose_key}

    async def generate_social_visual(
        self,
        texte_principal: str,
        sous_texte: str,
        format_key: str,
        style: str = "professionnel",
        pose_key: str = "presentation",
        sujet_context: str = "",
    ) -> dict:
        pose = next(
            (p for p in AVATAR_POSES if p["key"] == pose_key),
            {"description": "confident pose, looking at camera"},
        )
        fmt = VISUAL_FORMATS.get(format_key, VISUAL_FORMATS["1:1"])

        style_map = {
            "professionnel": "clean professional design, minimal, corporate tech",
            "moderne": "modern bold design, dynamic composition, energetic",
            "minimaliste": "ultra minimal design, lots of negative space, elegant",
        }
        style_desc = style_map.get(style, style_map["professionnel"])

        composition = (
            "portrait vertical composition, character top, text bottom"
            if format_key == "9:16"
            else "square composition, character left, text right"
            if format_key in ("1:1", "1:1_facebook")
            else "landscape composition, character left third, text center"
        )

        prompt = (
            f"Professional social media advertisement visual, "
            f"{CAPCORE_AVATAR_BASE_PROMPT}, "
            f"{pose['description']}, "
            f"{CAPCORE_BACKGROUND}, "
            f"large bold text overlay exactly '{texte_principal}', "
            f"subtitle text exactly '{sous_texte}', "
            f"all text in French language, text must be readable, "
            f"{style_desc}, "
            f"{composition}, "
            f"{'vertical' if format_key == '9:16' else 'square' if format_key in ('1:1', '1:1_facebook') else 'horizontal'} format, "
            f"high end advertising visual, no watermark"
        )

        if sujet_context:
            prompt += f", context: {sujet_context}"

        try:
            image_url = await self._call_replicate(
                prompt=prompt,
                width=fmt["width"],
                height=fmt["height"],
            )
            return {
                "image_url": image_url,
                "format": format_key,
                "format_label": fmt["label"],
                "texte_principal": texte_principal,
                "sous_texte": sous_texte,
                "prompt_used": prompt,
            }
        except Exception as e:
            return {"error": str(e), "format": format_key}


visual_agent = VisualAgent()

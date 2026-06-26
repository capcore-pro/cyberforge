# ============================================
# KLING SERVICE — CyberForge
# Client API Kling AI pour génération vidéo
# ============================================

import os
import httpx
import asyncio
import logging
from typing import Optional
from datetime import datetime
from supabase import create_client

logger = logging.getLogger(__name__)

KLING_API_BASE = "https://api.klingai.com"
KLING_API_KEY = os.getenv("KLING_API_KEY")

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)


class KlingService:

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {KLING_API_KEY}",
            "Content-Type": "application/json"
        }

    # ─────────────────────────────────────────
    # GÉNÉRER UN CLIP
    # ─────────────────────────────────────────
    async def generate_clip(
        self,
        project_id: str,
        clip_id: str,
        prompt: str,
        scene_number: int,
        duration: int = 5,
        model: str = "kling-v2-master",
        aspect_ratio: str = "16:9"
    ) -> dict:
        """Lance la génération d'un clip via l'API Kling."""

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{KLING_API_BASE}/v1/videos/text2video",
                headers=self.headers,
                json={
                    "model_name": model,
                    "prompt": prompt,
                    "duration": duration,
                    "aspect_ratio": aspect_ratio
                }
            )

        data = response.json()

        if data.get("code") != 0:
            logger.error(f"Kling error: {data}")
            await self._update_clip_status(clip_id, "failed", error=data.get("message"))
            raise Exception(f"Kling API error: {data.get('message')}")

        task_id = data["data"]["task_id"]

        # Sauvegarder task_id dans Supabase
        supabase.table("video_clips").update({
            "kling_task_id": task_id,
            "status": "processing"
        }).eq("id", clip_id).execute()

        logger.info(f"Clip {scene_number} submitted — task_id: {task_id}")
        return {"task_id": task_id, "status": "processing"}

    async def generate_image_to_video(
        self,
        image_base64: str,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "9:16",
        model: str = "kling-v2-master",
    ) -> dict:
        url = f"{KLING_API_BASE}/v1/videos/image2video"
        payload = {
            "model_name": model,
            "image": image_base64,
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()

        if data.get("code") != 0:
            raise Exception(f"Kling image2video error: {data.get('message', 'Unknown error')}")

        task_id = data["data"]["task_id"]
        return {"task_id": task_id, "status": "processing"}

    async def check_image_video_status(self, task_id: str) -> dict:
        url = f"{KLING_API_BASE}/v1/videos/image2video/{task_id}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()

        if data.get("code") != 0:
            raise Exception(f"Kling status error: {data.get('message', 'Unknown error')}")

        task_data = data["data"]
        status = task_data["task_status"]
        result = {"status": status, "task_id": task_id}

        if status == "succeed":
            result["video_url"] = task_data["task_result"]["videos"][0]["url"]
            result["duration"] = task_data["task_result"]["videos"][0].get("duration", 5)

        return result

    # ─────────────────────────────────────────
    # VÉRIFIER STATUT
    # ─────────────────────────────────────────
    async def check_clip_status(self, task_id: str) -> dict:
        """Vérifie le statut d'une tâche Kling."""

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{KLING_API_BASE}/v1/videos/text2video/{task_id}",
                headers=self.headers
            )

        data = response.json()

        if data.get("code") != 0:
            raise Exception(f"Kling status error: {data.get('message')}")

        task_data = data["data"]
        status = task_data["task_status"]

        result = {"status": status, "task_id": task_id}

        if status == "succeed":
            videos = task_data.get("task_result", {}).get("videos", [])
            if videos:
                result["url"] = videos[0]["url"]
                result["duration"] = videos[0].get("duration", 5)
                result["units_used"] = int(task_data.get("final_unit_deduction", 10))

        return result

    # ─────────────────────────────────────────
    # ATTENDRE ET RÉCUPÉRER UN CLIP
    # ─────────────────────────────────────────
    async def wait_for_clip(
        self,
        task_id: str,
        clip_id: str,
        max_wait: int = 300,
        poll_interval: int = 15
    ) -> Optional[str]:
        """Attend la fin de génération et retourne l'URL du clip."""

        elapsed = 0

        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            result = await self.check_clip_status(task_id)

            if result["status"] == "succeed":
                url = result["url"]
                units = result.get("units_used", 10)

                # Mettre à jour clip dans Supabase
                await self._update_clip_status(
                    clip_id, "done",
                    clip_url=url,
                    duration=result.get("duration", 5),
                    units_used=units
                )

                # Mettre à jour solde Kling
                await self._deduct_balance(units)

                logger.info(f"Clip done — {units} units used")
                return url

            elif result["status"] == "failed":
                await self._update_clip_status(clip_id, "failed", error="Kling generation failed")
                raise Exception(f"Clip generation failed for task {task_id}")

            else:
                logger.info(f"Clip {task_id} — {result['status']} ({elapsed}s)")

        raise Exception(f"Clip timeout after {max_wait}s")

    # ─────────────────────────────────────────
    # SOLDE KLING
    # ─────────────────────────────────────────
    async def get_balance(self) -> dict:
        """Retourne le solde Kling depuis Supabase."""

        result = supabase.table("kling_balance").select("*").limit(1).execute()

        if result.data:
            return result.data[0]

        return {"units_total": 0, "units_used": 0, "units_remaining": 0}

    async def recharge_balance(self, units_added: int) -> dict:
        """Ajoute des unités au solde Kling."""

        current = await self.get_balance()

        updated = supabase.table("kling_balance").update({
            "units_total": current["units_total"] + units_added,
            "last_recharged_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat()
        }).eq("id", current["id"]).execute()

        return updated.data[0] if updated.data else {}

    # ─────────────────────────────────────────
    # HELPERS PRIVÉS
    # ─────────────────────────────────────────
    async def _update_clip_status(
        self,
        clip_id: str,
        status: str,
        clip_url: str = None,
        duration: float = None,
        units_used: int = None,
        error: str = None
    ):
        update = {"status": status}
        if clip_url: update["clip_url"] = clip_url
        if duration: update["duration"] = duration
        if units_used: update["units_used"] = units_used
        if error: update["error_message"] = error

        supabase.table("video_clips").update(update).eq("id", clip_id).execute()

    async def _deduct_balance(self, units: int):
        current = await self.get_balance()

        supabase.table("kling_balance").update({
            "units_used": current["units_used"] + units,
            "last_updated": datetime.utcnow().isoformat()
        }).eq("id", current["id"]).execute()


# Instance globale
kling_service = KlingService()

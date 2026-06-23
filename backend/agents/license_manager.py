"""
LicenseManager — CyberForge
Gestion des licences One Shot et Abonnement pour les logiciels desktop clients.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from supabase import Client, create_client

from config import get_settings, plain_secret_str

logger = logging.getLogger(__name__)


def _supabase_client() -> Client:
    settings = get_settings()
    url = (settings.supabase_url or "").strip()
    key = plain_secret_str(settings.supabase_secret_key)
    if not url or not key:
        raise RuntimeError("Supabase non configuré (SUPABASE_URL / SUPABASE_SECRET_KEY).")
    return create_client(url, key)


class LicenseManager:
    """Crée et vérifie les licences desktop (one_shot / subscription)."""

    def __init__(self, client: Client | None = None) -> None:
        self._client = client

    @property
    def supabase(self) -> Client:
        if self._client is None:
            self._client = _supabase_client()
        return self._client

    def generate_license_key(self, build_id: str, model: str) -> str:
        """Génère une clé de licence unique."""
        _ = build_id  # réservé pour traçabilité future (checksum, etc.)
        prefix = "CF-ONE" if model == "one_shot" else "CF-SUB"
        unique = str(uuid.uuid4()).upper().replace("-", "")[:16]
        return f"{prefix}-{unique[:4]}-{unique[4:8]}-{unique[8:12]}-{unique[12:16]}"

    async def create_license(
        self,
        build_id: str,
        client_email: str,
        model: str,
        stripe_customer_id: str | None = None,
        stripe_subscription_id: str | None = None,
    ) -> dict[str, Any]:
        """Crée une licence dans Supabase."""
        license_key = self.generate_license_key(build_id, model)

        data = {
            "build_id": build_id,
            "client_email": client_email.strip(),
            "license_key": license_key,
            "model": model,
            "stripe_customer_id": stripe_customer_id,
            "stripe_subscription_id": stripe_subscription_id,
            "is_active": True,
        }

        result = self.supabase.table("electron_licenses").insert(data).execute()

        if result.data:
            logger.info("Licence créée : %s (%s)", license_key, model)
            return dict(result.data[0])

        raise RuntimeError("Erreur création licence Supabase")

    async def check_license(self, license_key: str) -> dict[str, Any]:
        """
        Vérifie si une licence est active.
        Appelé par le .exe au démarrage (modèle abonnement).
        """
        key = license_key.strip()
        if not key:
            return {"active": False, "reason": "Licence introuvable"}

        try:
            result = (
                self.supabase.table("electron_licenses")
                .select("*")
                .eq("license_key", key)
                .single()
                .execute()
            )

            if not result.data:
                return {"active": False, "reason": "Licence introuvable"}

            row = dict(result.data)

            if row.get("model") == "one_shot":
                return {"active": True, "model": "one_shot"}

            if not row.get("is_active", False):
                return {"active": False, "reason": "Abonnement expiré ou annulé"}

            self.supabase.table("electron_licenses").update(
                {"last_check": datetime.now(UTC).isoformat()}
            ).eq("license_key", key).execute()

            return {
                "active": True,
                "model": "subscription",
                "client_email": row.get("client_email"),
            }

        except Exception as exc:
            logger.error("LicenseManager check error: %s", exc)
            return {"active": False, "reason": "Erreur vérification"}

    async def deactivate_license(self, license_key: str) -> bool:
        """Désactive une licence (abonnement annulé)."""
        try:
            self.supabase.table("electron_licenses").update({"is_active": False}).eq(
                "license_key", license_key.strip()
            ).execute()
            logger.info("Licence désactivée : %s", license_key)
            return True
        except Exception as exc:
            logger.error("Deactivate license error: %s", exc)
            return False

    async def get_all_licenses(self) -> list[dict[str, Any]]:
        """Retourne toutes les licences pour le dashboard CyberForge."""
        try:
            result = (
                self.supabase.table("electron_licenses")
                .select("*, electron_builds(app_name, client_name, model)")
                .order("created_at", desc=True)
                .execute()
            )
            return [dict(row) for row in (result.data or [])]
        except Exception as exc:
            logger.error("Get all licenses error: %s", exc)
            return []


license_manager = LicenseManager()

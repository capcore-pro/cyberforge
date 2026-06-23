"""
PortalAgent — CyberForge
Gère les clients du portail, leurs sites et les redéploiements.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import UTC, datetime
from typing import Any

from supabase import Client, create_client

from config import get_settings, plain_secret_str
from tools.export_cloudflare import deploy_html_demo

logger = logging.getLogger(__name__)


def _supabase_client() -> Client:
    settings = get_settings()
    url = (settings.supabase_url or "").strip()
    key = plain_secret_str(settings.supabase_secret_key)
    if not url or not key:
        raise RuntimeError("Supabase non configuré (SUPABASE_URL / SUPABASE_SECRET_KEY).")
    return create_client(url, key)


class PortalAgent:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client

    @property
    def supabase(self) -> Client:
        if self._client is None:
            self._client = _supabase_client()
        return self._client

    async def create_client(
        self,
        email: str,
        full_name: str,
        company: str = "",
        plan: str = "starter",
        password: str | None = None,
    ) -> dict[str, Any]:
        """Crée un client portail. Mat l'active manuellement."""
        if not password:
            password = secrets.token_urlsafe(10)

        password_hash = hashlib.sha256(password.encode()).hexdigest()

        supabase_user_id: str | None = None
        try:
            auth_result = self.supabase.auth.admin.create_user(
                {
                    "email": email,
                    "password": password,
                    "email_confirm": True,
                }
            )
            if auth_result.user:
                supabase_user_id = str(auth_result.user.id)
        except Exception as e:
            logger.warning("Supabase Auth create user error: %s", e)

        result = (
            self.supabase.table("portal_clients")
            .insert(
                {
                    "email": email,
                    "full_name": full_name,
                    "company": company,
                    "plan": plan,
                    "password_hash": password_hash,
                    "supabase_user_id": supabase_user_id,
                    "is_active": True,
                }
            )
            .execute()
        )

        client = dict(result.data[0]) if result.data else {}
        client["temp_password"] = password
        return client

    async def list_clients(self) -> list[dict[str, Any]]:
        """Liste tous les clients portail."""
        result = (
            self.supabase.table("portal_clients")
            .select("*, portal_sites(count)")
            .order("created_at", desc=True)
            .execute()
        )
        return list(result.data or [])

    async def toggle_client(self, client_id: str, is_active: bool) -> bool:
        """Active/désactive un client."""
        self.supabase.table("portal_clients").update({"is_active": is_active}).eq(
            "id", client_id
        ).execute()
        return True

    async def add_site(
        self,
        client_id: str,
        site_name: str,
        html_content: str,
        site_url: str = "",
        cloudflare_project_name: str = "",
        sector: str = "",
        project_type: str = "vitrine_next",
        project_id: str = "",
    ) -> dict[str, Any]:
        """Ajoute un site au portail d'un client."""
        result = (
            self.supabase.table("portal_sites")
            .insert(
                {
                    "client_id": client_id,
                    "project_id": project_id,
                    "site_name": site_name,
                    "site_url": site_url,
                    "cloudflare_project_name": cloudflare_project_name,
                    "html_content": html_content,
                    "html_backup": html_content,
                    "sector": sector,
                    "project_type": project_type,
                    "status": "active",
                }
            )
            .execute()
        )
        return dict(result.data[0]) if result.data else {}

    async def get_client_sites(self, client_id: str) -> list[dict[str, Any]]:
        """Retourne les sites d'un client."""
        result = (
            self.supabase.table("portal_sites")
            .select("*")
            .eq("client_id", client_id)
            .eq("status", "active")
            .order("created_at", desc=True)
            .execute()
        )
        return list(result.data or [])

    async def save_and_deploy(
        self,
        site_id: str,
        client_id: str,
        edits: list[dict[str, Any]],
        html_updated: str,
    ) -> dict[str, Any]:
        """
        Sauvegarde les modifications et redéploie sur Cloudflare.
        Appelé quand le client clique "Enregistrer" dans le portail.
        """
        site_result = (
            self.supabase.table("portal_sites")
            .select("*")
            .eq("id", site_id)
            .single()
            .execute()
        )

        if not site_result.data:
            raise RuntimeError("Site introuvable")

        site = site_result.data
        now = datetime.now(UTC).isoformat()

        for edit in edits:
            self.supabase.table("portal_edits").insert(
                {
                    "site_id": site_id,
                    "client_id": client_id,
                    "edit_type": edit.get("type", "text"),
                    "element_selector": edit.get("selector", ""),
                    "old_value": edit.get("old_value", ""),
                    "new_value": edit.get("new_value", ""),
                    "deployed": False,
                }
            ).execute()

        self.supabase.table("portal_sites").update(
            {
                "html_content": html_updated,
                "updated_at": now,
            }
        ).eq("id", site_id).execute()

        deploy_result: dict[str, Any] = {
            "url": site.get("site_url"),
            "success": False,
        }

        try:
            production_url, demo_token, _, _ = await deploy_html_demo(
                html=html_updated,
                title=str(site.get("site_name") or ""),
                project_type=str(site.get("project_type") or "vitrine_next"),
            )
            deploy_result = {"url": production_url, "success": True}

            self.supabase.table("portal_sites").update(
                {
                    "site_url": production_url,
                    "cloudflare_project_name": demo_token,
                    "last_deployed_at": now,
                }
            ).eq("id", site_id).execute()

            self.supabase.table("portal_edits").update({"deployed": True}).eq(
                "site_id", site_id
            ).eq("deployed", False).execute()

        except Exception as e:
            logger.error("PortalAgent deploy error: %s", e)
            deploy_result["error"] = str(e)

        return {
            "success": deploy_result["success"],
            "url": deploy_result.get("url"),
            "edits_saved": len(edits),
        }

    async def verify_client(self, email: str, password: str) -> dict[str, Any] | None:
        """Vérifie les credentials d'un client portail."""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        result = (
            self.supabase.table("portal_clients")
            .select("*")
            .eq("email", email)
            .eq("password_hash", password_hash)
            .eq("is_active", True)
            .single()
            .execute()
        )
        return dict(result.data) if result.data else None


portal_agent = PortalAgent()

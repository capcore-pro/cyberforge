"""
Sous-domaines automatiques nom-client.capcore.pro via Cloudflare DNS API.
"""

from __future__ import annotations

import logging
import re
import unicodedata

import httpx

from config import Settings, get_settings, plain_secret_str
from security.cloudflare_env import get_cloudflare_credentials

logger = logging.getLogger(__name__)

API_BASE = "https://api.cloudflare.com/client/v4"


class SubdomainError(Exception):
    """Erreur création / suppression sous-domaine Cloudflare."""


class SubdomainService:
    """
    Crée automatiquement des sous-domaines
    nom-client.capcore.pro via Cloudflare DNS API.
    """

    BASE_DOMAIN = "capcore.pro"
    PAGES_TARGET = "cyberforge-demos.pages.dev"

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def slugify(self, name: str) -> str:
        """
        "Restaurant Le Provençal" → "restaurant-le-provencal"
        Minuscules, accents supprimés, espaces → tirets, max 50 chars.
        """
        normalized = unicodedata.normalize("NFD", name or "")
        ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
        lowered = ascii_name.lower()
        cleaned = re.sub(r"[^a-z0-9\s-]", "", lowered)
        dashed = re.sub(r"\s+", "-", cleaned.strip())
        collapsed = re.sub(r"-+", "-", dashed)
        return collapsed[:50].strip("-")

    async def create_subdomain(
        self,
        client_name: str,
        project_id: str | None = None,
    ) -> dict[str, str]:
        """
        Crée restaurant-le-provencal.capcore.pro → CNAME vers cyberforge-demos.pages.dev.
        project_id est ignoré ici (mise à jour Supabase faite par la route API).
        """
        _ = project_id
        zone_id = (self._settings.cloudflare_zone_id or "").strip()
        if not zone_id:
            raise SubdomainError("CLOUDFLARE_ZONE_ID non configuré")

        slug = self.slugify(client_name)
        if not slug:
            raise SubdomainError("Nom client invalide pour sous-domaine")

        subdomain = f"{slug}.{self.BASE_DOMAIN}"

        existing = await self._get_dns_record(slug)
        if existing:
            return {
                "subdomain": slug,
                "url": f"https://{subdomain}",
                "dns_record_id": str(existing["id"]),
                "status": "already_exists",
            }

        record = await self._create_cname(slug, self.PAGES_TARGET)
        logger.info(
            "[SubdomainService] créé %s → %s (id=%s)",
            subdomain,
            self.PAGES_TARGET,
            record.get("id"),
        )
        return {
            "subdomain": slug,
            "url": f"https://{subdomain}",
            "dns_record_id": str(record["id"]),
            "status": "created",
        }

    async def delete_subdomain(self, client_name: str) -> bool:
        """Supprime le sous-domaine DNS."""
        slug = self.slugify(client_name)
        if not slug:
            return True
        record = await self._get_dns_record(slug)
        if not record:
            return True
        return await self._delete_dns_record(str(record["id"]))

    async def list_subdomains(self) -> list[dict[str, str]]:
        """Liste les enregistrements CNAME capcore.pro."""
        zone_id = (self._settings.cloudflare_zone_id or "").strip()
        if not zone_id:
            raise SubdomainError("CLOUDFLARE_ZONE_ID non configuré")

        url = f"{API_BASE}/zones/{zone_id}/dns_records?type=CNAME&per_page=100"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._headers())
            data = self._parse_response(response, "list_dns_records")
            return [
                {
                    "name": str(r["name"]),
                    "content": str(r["content"]),
                    "id": str(r["id"]),
                    "created_on": str(r.get("created_on") or ""),
                }
                for r in data.get("result", [])
                if self.BASE_DOMAIN in str(r.get("name") or "")
            ]

    async def _get_dns_record(self, slug: str) -> dict | None:
        zone_id = (self._settings.cloudflare_zone_id or "").strip()
        if not zone_id:
            return None
        url = (
            f"{API_BASE}/zones/{zone_id}/dns_records"
            f"?type=CNAME&name={slug}.{self.BASE_DOMAIN}"
        )
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._headers())
            data = self._parse_response(response, "get_dns_record")
            results = data.get("result", [])
            return results[0] if results else None

    async def _create_cname(self, slug: str, target: str) -> dict:
        zone_id = (self._settings.cloudflare_zone_id or "").strip()
        url = f"{API_BASE}/zones/{zone_id}/dns_records"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers=self._headers(),
                json={
                    "type": "CNAME",
                    "name": f"{slug}.{self.BASE_DOMAIN}",
                    "content": target,
                    "ttl": 1,
                    "proxied": True,
                },
            )
            data = self._parse_response(response, "create_cname")
            result = data.get("result")
            if not isinstance(result, dict):
                raise SubdomainError("Réponse Cloudflare DNS incomplète")
            return result

    async def _delete_dns_record(self, record_id: str) -> bool:
        zone_id = (self._settings.cloudflare_zone_id or "").strip()
        url = f"{API_BASE}/zones/{zone_id}/dns_records/{record_id}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(url, headers=self._headers())
            data = self._parse_response(response, "delete_dns_record")
            return bool(data.get("success", False))

    def _headers(self) -> dict[str, str]:
        credentials = get_cloudflare_credentials()
        token = credentials.api_token if credentials else ""
        if not token:
            token = plain_secret_str(self._settings.cloudflare_api_token)
        if not token:
            raise SubdomainError("CLOUDFLARE_API_TOKEN non configuré")
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _parse_response(self, response: httpx.Response, context: str) -> dict:
        try:
            data = response.json()
        except Exception as exc:
            raise SubdomainError(
                f"Réponse Cloudflare invalide ({context}, HTTP {response.status_code})"
            ) from exc
        if not data.get("success"):
            errors = data.get("errors") or []
            messages = "; ".join(
                str(e.get("message", e)) for e in errors if isinstance(e, dict)
            ) or f"Échec Cloudflare ({context})"
            raise SubdomainError(messages)
        return data


subdomain_service = SubdomainService()

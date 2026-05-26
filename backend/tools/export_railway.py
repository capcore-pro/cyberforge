"""
Export Railway — création de projet pour apps backend / full-stack.
"""

from __future__ import annotations

import logging
import re

import httpx

from config import Settings, get_settings, plain_secret_str

logger = logging.getLogger(__name__)

RAILWAY_GRAPHQL = "https://backboard.railway.com/graphql/v2"


class RailwayExportError(Exception):
    """Échec export Railway."""


async def deploy_to_railway(
    *,
    project_name: str,
    settings: Settings | None = None,
) -> tuple[str, str]:
    """
    Crée un projet Railway et retourne (production_url, project_id).
  """
    resolved = settings or get_settings()
    token = plain_secret_str(resolved.railway_api_key)
    if not token:
        raise RailwayExportError("RAILWAY_API_KEY non configurée.")

    safe_name = re.sub(r"[^\w\s-]", "", project_name)[:60].strip() or "CyberForge App"
    query = """
    mutation projectCreate($name: String!) {
      projectCreate(input: { name: $name }) {
        id
        name
      }
    }
    """
    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post(
            RAILWAY_GRAPHQL,
            json={"query": query, "variables": {"name": safe_name}},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )

    if resp.status_code >= 400:
        raise RailwayExportError(f"Railway HTTP {resp.status_code}: {resp.text[:300]}")

    payload = resp.json()
    errors = payload.get("errors")
    if errors:
        msg = errors[0].get("message", str(errors)) if isinstance(errors, list) else str(errors)
        raise RailwayExportError(msg)

    data = (payload.get("data") or {}).get("projectCreate") or {}
    project_id = data.get("id")
    if not project_id:
        raise RailwayExportError("Railway n'a pas renvoyé d'identifiant projet.")

    production_url = f"https://railway.app/project/{project_id}"
    return production_url, str(project_id)

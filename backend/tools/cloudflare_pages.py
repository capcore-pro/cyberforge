"""
Déploiement HTML autonome sur Cloudflare Pages (Direct Upload API).
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

API_BASE = "https://api.cloudflare.com/client/v4"


class CloudflarePagesError(Exception):
    """Erreur API Cloudflare Pages (message sûr pour le client)."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class CloudflareDeployResult:
    project_name: str
    deployment_id: str
    url: str


def pages_project_name_for_token(token: str) -> str:
    """Nom de projet Pages valide (a-z0-9-), préfixe cf-."""
    slug = re.sub(r"[^a-z0-9]", "-", token.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)[:40] or "demo"
    return f"cf-{slug}"


def _file_digest(path: str, body: bytes) -> str:
    """
    Empreinte fichier pour le manifest Pages.
    Cloudflare utilise blake3(body + path) ; fallback SHA-256 identique côté API v4.
    """
    try:
        import blake3  # type: ignore[import-untyped]

        hasher = blake3.blake3()
        hasher.update(body)
        hasher.update(path.encode("utf-8"))
        return hasher.hexdigest()
    except ImportError:
        return hashlib.sha256(body + path.encode("utf-8")).hexdigest()


def _api_headers(api_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_token}"}


def _check_response(resp: httpx.Response, context: str) -> dict[str, Any]:
    try:
        payload = resp.json()
    except json.JSONDecodeError as exc:
        raise CloudflarePagesError(
            f"Réponse Cloudflare invalide ({context}).",
            status_code=resp.status_code,
        ) from exc
    if not payload.get("success"):
        errors = payload.get("errors") or []
        msg = "; ".join(
            str(e.get("message", e)) for e in errors if isinstance(e, dict)
        ) or f"Échec Cloudflare ({context})."
        raise CloudflarePagesError(msg, status_code=resp.status_code)
    result = payload.get("result")
    if not isinstance(result, dict):
        raise CloudflarePagesError(
            f"Réponse Cloudflare incomplète ({context}).",
            status_code=resp.status_code,
        )
    return result


async def _ensure_project(
    client: httpx.AsyncClient,
    *,
    account_id: str,
    api_token: str,
    project_name: str,
) -> None:
    url = f"{API_BASE}/accounts/{account_id}/pages/projects"
    resp = await client.post(
        url,
        headers=_api_headers(api_token),
        json={"name": project_name, "production_branch": "main"},
    )
    if resp.status_code == 409:
        return
    if resp.is_success:
        _check_response(resp, "create_project")
        return
    if resp.status_code == 400:
        detail = resp.text.lower()
        if "already exists" in detail or "duplicate" in detail:
            return
    _check_response(resp, "create_project")


async def _get_upload_token(
    client: httpx.AsyncClient,
    *,
    account_id: str,
    api_token: str,
    project_name: str,
) -> str:
    url = (
        f"{API_BASE}/accounts/{account_id}/pages/projects/"
        f"{project_name}/upload-token"
    )
    resp = await client.get(url, headers=_api_headers(api_token))
    result = _check_response(resp, "upload_token")
    jwt = result.get("jwt") or result.get("token")
    if not isinstance(jwt, str) or not jwt.strip():
        raise CloudflarePagesError("Jeton d'upload Cloudflare manquant.")
    return jwt.strip()


async def _upload_asset(
    client: httpx.AsyncClient,
    *,
    upload_jwt: str,
    path: str,
    body: bytes,
    content_type: str,
    digest: str,
) -> None:
    url = f"{API_BASE}/pages/assets/upload"
    payload = [
        {
            "key": digest,
            "value": base64.b64encode(body).decode("ascii"),
            "metadata": {"contentType": content_type},
            "base64": True,
        }
    ]
    resp = await client.post(
        url,
        headers={"Authorization": f"Bearer {upload_jwt}"},
        json=payload,
    )
    _check_response(resp, "upload_asset")


async def _upsert_hashes(
    client: httpx.AsyncClient,
    *,
    upload_jwt: str,
    digests: list[str],
) -> None:
    url = f"{API_BASE}/pages/assets/upsert-hashes"
    resp = await client.post(
        url,
        headers={"Authorization": f"Bearer {upload_jwt}"},
        json={"hashes": digests},
    )
    _check_response(resp, "upsert_hashes")


async def _create_deployment(
    client: httpx.AsyncClient,
    *,
    account_id: str,
    api_token: str,
    project_name: str,
    manifest: dict[str, str],
) -> str:
    url = (
        f"{API_BASE}/accounts/{account_id}/pages/projects/"
        f"{project_name}/deployments"
    )
    resp = await client.post(
        url,
        headers=_api_headers(api_token),
        data={"manifest": json.dumps(manifest)},
    )
    result = _check_response(resp, "create_deployment")
    deployment_id = str(result.get("id") or "")
    if not deployment_id:
        raise CloudflarePagesError("Identifiant de déploiement Cloudflare manquant.")
    return deployment_id


async def _wait_deployment_ready(
    client: httpx.AsyncClient,
    *,
    account_id: str,
    api_token: str,
    project_name: str,
    deployment_id: str,
    timeout_s: float = 120.0,
) -> str:
    url = (
        f"{API_BASE}/accounts/{account_id}/pages/projects/"
        f"{project_name}/deployments/{deployment_id}"
    )
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        resp = await client.get(url, headers=_api_headers(api_token))
        result = _check_response(resp, "get_deployment")
        stage = result.get("latest_stage") or {}
        status = str(stage.get("status") or "").lower()
        if status == "success":
            aliases = result.get("aliases")
            if isinstance(aliases, list) and aliases:
                return str(aliases[0])
            url_out = result.get("url")
            if isinstance(url_out, str) and url_out.strip():
                return url_out.strip()
            return f"https://{project_name}.pages.dev"
        if status in ("failure", "canceled"):
            raise CloudflarePagesError(
                f"Déploiement Cloudflare en échec (statut {status})."
            )
        await asyncio.sleep(2.0)
    raise CloudflarePagesError("Délai dépassé en attendant le déploiement Cloudflare.")


async def deploy_standalone_html(
    *,
    account_id: str,
    api_token: str,
    project_name: str,
    html: str,
) -> CloudflareDeployResult:
    """
    Publie index.html sur un projet Cloudflare Pages (création projet si besoin).
    """
    body = html.encode("utf-8")
    path = "index.html"
    digest = _file_digest(path, body)

    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=15.0)) as client:
        await _ensure_project(
            client,
            account_id=account_id,
            api_token=api_token,
            project_name=project_name,
        )
        upload_jwt = await _get_upload_token(
            client,
            account_id=account_id,
            api_token=api_token,
            project_name=project_name,
        )
        await _upload_asset(
            client,
            upload_jwt=upload_jwt,
            path=path,
            body=body,
            content_type="text/html; charset=utf-8",
            digest=digest,
        )
        await _upsert_hashes(client, upload_jwt=upload_jwt, digests=[digest])
        deployment_id = await _create_deployment(
            client,
            account_id=account_id,
            api_token=api_token,
            project_name=project_name,
            manifest={path: digest},
        )
        live_url = await _wait_deployment_ready(
            client,
            account_id=account_id,
            api_token=api_token,
            project_name=project_name,
            deployment_id=deployment_id,
        )

    if not live_url.startswith("http"):
        live_url = f"https://{project_name}.pages.dev"

    logger.info(
        "Démo déployée sur Cloudflare Pages: project=%s url=%s",
        project_name,
        live_url,
    )
    return CloudflareDeployResult(
        project_name=project_name,
        deployment_id=deployment_id,
        url=live_url.rstrip("/"),
    )

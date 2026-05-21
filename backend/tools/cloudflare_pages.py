"""
Déploiement HTML autonome sur Cloudflare Pages (Direct Upload API).
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

API_BASE = "https://api.cloudflare.com/client/v4"
# Version algorithme hash (Wrangler blake3) — visible dans les logs au reload.
HASH_ALGO_VERSION = "wrangler-blake3-b64-ext-v1"
# TEMP DEBUG — print() stderr vers console uvicorn (retirer après diagnostic).
CF_PAGES_DEBUG_PRINT = False


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


def _file_extension(file_path: str) -> str:
    """Extension sans point, comme extname(path).substring(1) dans Wrangler."""
    name = file_path.replace("\\", "/").rsplit("/", 1)[-1]
    dot = name.rfind(".")
    return name[dot + 1 :] if dot >= 0 else ""


def _file_digest(file_path: str, body: bytes) -> str:
    """
    Empreinte fichier pour Direct Upload (compatible Wrangler pages/hash.ts).

    blake3( base64(contenu) + extension )[:32] — pas blake3(body + chemin).
    """
    try:
        import blake3  # type: ignore[import-untyped]
    except ImportError as exc:
        raise CloudflarePagesError(
            "Dépendance blake3 manquante pour le déploiement Cloudflare Pages."
        ) from exc

    b64 = base64.b64encode(body).decode("ascii")
    digest_input = (b64 + _file_extension(file_path)).encode("utf-8")
    return blake3.blake3(digest_input).hexdigest()[:32]


def _manifest_path(file_path: str) -> str:
    """Chemin manifest avec slash initial (ex. /index.html)."""
    normalized = file_path.replace("\\", "/").lstrip("/")
    return f"/{normalized}"


def _api_headers(api_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_token}"}


def _mask_account_id(account_id: str) -> str:
    aid = account_id.strip()
    if len(aid) <= 8:
        return "***"
    return f"{aid[:4]}…{aid[-4:]}"


def _response_body_for_log(resp: httpx.Response, *, limit: int = 2000) -> str:
    try:
        text = resp.text
    except Exception as exc:
        return f"<lecture impossible: {exc}>"
    if len(text) <= limit:
        return text
    return f"{text[:limit]}… [tronqué, {len(text)} octets]"


def _log_deploy_step(step: str, message: str, **extra: Any) -> None:
    parts = [f"[Cloudflare Pages] {step}: {message}"]
    for key, value in extra.items():
        parts.append(f"{key}={value}")
    logger.info(" | ".join(parts))


def _sanitize_payload_for_print(data: Any) -> Any:
    """Masque JWT / base64 volumineux dans les dumps console."""
    if isinstance(data, dict):
        out: dict[str, Any] = {}
        for key, value in data.items():
            lk = str(key).lower()
            if lk in ("jwt", "token") and isinstance(value, str):
                out[key] = f"<redacted len={len(value)}>"
            elif lk == "value" and isinstance(value, str) and len(value) > 120:
                out[key] = f"<base64 len={len(value)}>"
            elif lk == "authorization":
                out[key] = "<redacted>"
            else:
                out[key] = _sanitize_payload_for_print(value)
        return out
    if isinstance(data, list):
        return [_sanitize_payload_for_print(item) for item in data]
    return data


def _debug_print(
    step: str,
    *,
    phase: str,
    http_status: int | None = None,
    url: str | None = None,
    request_body: Any = None,
    response: httpx.Response | None = None,
) -> None:
    if not CF_PAGES_DEBUG_PRINT:
        return
    lines = [f"\n=== [CF-PAGES-DEBUG] {step} | {phase} ==="]
    if url:
        lines.append(f"URL: {url}")
    if http_status is not None:
        lines.append(f"HTTP: {http_status}")
    if request_body is not None:
        lines.append(
            "REQUEST: "
            + json.dumps(
                _sanitize_payload_for_print(request_body),
                ensure_ascii=False,
                indent=2,
            )
        )
    if response is not None:
        lines.append(f"RESPONSE RAW ({len(response.content)} bytes):")
        lines.append(_response_body_for_log(response, limit=8000))
    print("\n".join(lines), flush=True)


def _log_deploy_failure(step: str, resp: httpx.Response, *, context: str) -> None:
    logger.error(
        "[Cloudflare Pages] %s: ÉCHEC HTTP %s | url=%s | context=%s | body=%s",
        step,
        resp.status_code,
        resp.request.url if resp.request else "?",
        context,
        _response_body_for_log(resp),
    )


def _check_response(resp: httpx.Response, context: str) -> dict[str, Any]:
    try:
        payload = resp.json()
    except json.JSONDecodeError as exc:
        _log_deploy_failure(context, resp, context=f"{context}_invalid_json")
        raise CloudflarePagesError(
            f"Réponse Cloudflare invalide ({context}).",
            status_code=resp.status_code,
        ) from exc
    if not payload.get("success"):
        _log_deploy_failure(context, resp, context=context)
        errors = payload.get("errors") or []
        msg = "; ".join(
            str(e.get("message", e)) for e in errors if isinstance(e, dict)
        ) or f"Échec Cloudflare ({context})."
        if context == "upsert_hashes":
            msg += (
                " (upsert-hashes : body JSON {\"hashes\": [\"...\"]} avec JWT d'upload.)"
            )
        if context == "create_deployment":
            msg += (
                " (create deployment : manifest en multipart/form-data, pas urlencoded.)"
            )
        raise CloudflarePagesError(msg, status_code=resp.status_code)
    result = payload.get("result")
    # upsert-hashes renvoie souvent success:true sans corps result (null / absent).
    if context == "upsert_hashes":
        return result if isinstance(result, dict) else {}
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
    step = "1/5 create_project"
    url = f"{API_BASE}/accounts/{account_id}/pages/projects"
    body = {"name": project_name, "production_branch": "main"}
    _log_deploy_step(
        step,
        "début POST",
        account=_mask_account_id(account_id),
        project=project_name,
        url=url,
    )
    started = time.monotonic()
    _debug_print(step, phase="request", url=url, request_body=body)
    resp = await client.post(
        url,
        headers=_api_headers(api_token),
        json=body,
    )
    _debug_print(
        step,
        phase="response",
        http_status=resp.status_code,
        url=str(resp.request.url) if resp.request else url,
        response=resp,
    )
    elapsed_ms = int((time.monotonic() - started) * 1000)
    if resp.status_code == 409:
        _log_deploy_step(step, "projet déjà existant (409)", elapsed_ms=elapsed_ms)
        return
    if resp.is_success:
        result = _check_response(resp, "create_project")
        _log_deploy_step(
            step,
            "OK",
            elapsed_ms=elapsed_ms,
            project_id=result.get("id", "?"),
        )
        return
    if resp.status_code == 400:
        detail = resp.text.lower()
        if "already exists" in detail or "duplicate" in detail:
            _log_deploy_step(step, "projet déjà existant (400)", elapsed_ms=elapsed_ms)
            return
    _log_deploy_failure(step, resp, context="create_project")
    _check_response(resp, "create_project")


async def _get_upload_token(
    client: httpx.AsyncClient,
    *,
    account_id: str,
    api_token: str,
    project_name: str,
) -> str:
    step = "2/5 upload_token"
    url = (
        f"{API_BASE}/accounts/{account_id}/pages/projects/"
        f"{project_name}/upload-token"
    )
    _log_deploy_step(step, "début GET", project=project_name, url=url)
    started = time.monotonic()
    _debug_print(step, phase="request", url=url)
    resp = await client.get(url, headers=_api_headers(api_token))
    _debug_print(
        step,
        phase="response",
        http_status=resp.status_code,
        url=str(resp.request.url) if resp.request else url,
        response=resp,
    )
    elapsed_ms = int((time.monotonic() - started) * 1000)
    result = _check_response(resp, "upload_token")
    jwt = result.get("jwt") or result.get("token")
    if not isinstance(jwt, str) or not jwt.strip():
        _log_deploy_failure(step, resp, context="upload_token_missing_jwt")
        raise CloudflarePagesError("Jeton d'upload Cloudflare manquant.")
    _log_deploy_step(step, "OK", elapsed_ms=elapsed_ms, jwt_chars=len(jwt.strip()))
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
    step = "3/5 upload_asset"
    url = f"{API_BASE}/pages/assets/upload"
    payload = [
        {
            "key": digest,
            "value": base64.b64encode(body).decode("ascii"),
            "metadata": {"contentType": content_type},
            "base64": True,
        }
    ]
    _log_deploy_step(
        step,
        "début POST",
        path=path,
        digest=digest,
        bytes=len(body),
        content_type=content_type,
        url=url,
    )
    started = time.monotonic()
    _debug_print(
        step,
        phase="request",
        url=url,
        request_body=payload,
    )
    resp = await client.post(
        url,
        headers={"Authorization": f"Bearer {upload_jwt}"},
        json=payload,
    )
    _debug_print(
        step,
        phase="response",
        http_status=resp.status_code,
        url=str(resp.request.url) if resp.request else url,
        response=resp,
    )
    elapsed_ms = int((time.monotonic() - started) * 1000)
    result = _check_response(resp, "upload_asset")
    _log_deploy_step(
        step,
        "OK",
        elapsed_ms=elapsed_ms,
        successful_keys=result.get("successful_key_count"),
        unsuccessful=result.get("unsuccessful_keys"),
    )


async def _upsert_hashes(
    client: httpx.AsyncClient,
    *,
    upload_jwt: str,
    digests: list[str],
) -> None:
    step = "3b/5 upsert_hashes"
    url = f"{API_BASE}/pages/assets/upsert-hashes"
    body = {"hashes": digests}
    _log_deploy_step(
        step,
        "début POST",
        hash_count=len(digests),
        hashes=digests,
        url=url,
    )
    started = time.monotonic()
    _debug_print(step, phase="request", url=url, request_body=body)
    resp = await client.post(
        url,
        headers={"Authorization": f"Bearer {upload_jwt}"},
        json=body,
    )
    _debug_print(
        step,
        phase="response",
        http_status=resp.status_code,
        url=str(resp.request.url) if resp.request else url,
        response=resp,
    )
    elapsed_ms = int((time.monotonic() - started) * 1000)
    _check_response(resp, "upsert_hashes")
    _log_deploy_step(
        step,
        "OK",
        elapsed_ms=elapsed_ms,
        http_status=resp.status_code,
        body_preview=_response_body_for_log(resp, limit=200),
    )


async def _create_deployment(
    client: httpx.AsyncClient,
    *,
    account_id: str,
    api_token: str,
    project_name: str,
    manifest: dict[str, str],
) -> str:
    """
    Crée le déploiement (Direct Upload).

    Le manifest doit être envoyé en multipart/form-data (comme Wrangler),
    pas en application/x-www-form-urlencoded.
    """
    url = (
        f"{API_BASE}/accounts/{account_id}/pages/projects/"
        f"{project_name}/deployments"
    )
    step = "4/5 create_deployment"
    manifest_json = json.dumps(manifest)
    _log_deploy_step(
        step,
        "début POST multipart",
        project=project_name,
        manifest=manifest,
        manifest_bytes=len(manifest_json.encode("utf-8")),
        url=url,
    )
    started = time.monotonic()
    _debug_print(
        step,
        phase="request",
        url=url,
        request_body={
            "multipart": True,
            "manifest": manifest,
            "manifest_json": manifest_json,
        },
    )
    resp = await client.post(
        url,
        headers=_api_headers(api_token),
        files={
            "manifest": (None, manifest_json, "application/json"),
        },
    )
    _debug_print(
        step,
        phase="response",
        http_status=resp.status_code,
        url=str(resp.request.url) if resp.request else url,
        response=resp,
    )
    elapsed_ms = int((time.monotonic() - started) * 1000)
    result = _check_response(resp, "create_deployment")
    deployment_id = str(result.get("id") or "")
    if not deployment_id:
        _log_deploy_failure(step, resp, context="create_deployment_missing_id")
        raise CloudflarePagesError("Identifiant de déploiement Cloudflare manquant.")
    _log_deploy_step(
        step,
        "OK",
        elapsed_ms=elapsed_ms,
        deployment_id=deployment_id,
        deploy_url=result.get("url"),
        environment=result.get("environment"),
    )
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
    step = "5/5 wait_deployment"
    _log_deploy_step(
        step,
        "début polling",
        deployment_id=deployment_id,
        timeout_s=timeout_s,
        url=url,
    )
    deadline = time.monotonic() + timeout_s
    poll = 0
    while time.monotonic() < deadline:
        poll += 1
        resp = await client.get(url, headers=_api_headers(api_token))
        result = _check_response(resp, "get_deployment")
        stage = result.get("latest_stage") or {}
        status = str(stage.get("status") or "").lower()
        stage_name = str(stage.get("name") or "")
        _log_deploy_step(
            step,
            f"poll #{poll}",
            stage=stage_name,
            status=status or "?",
        )
        if status == "success":
            aliases = result.get("aliases")
            if isinstance(aliases, list) and aliases:
                return str(aliases[0])
            url_out = result.get("url")
            if isinstance(url_out, str) and url_out.strip():
                return url_out.strip()
            return f"https://{project_name}.pages.dev"
        if status in ("failure", "canceled"):
            _log_deploy_failure(step, resp, context=f"deployment_{status}")
            raise CloudflarePagesError(
                f"Déploiement Cloudflare en échec (statut {status})."
            )
        await asyncio.sleep(2.0)
    logger.error(
        "[Cloudflare Pages] %s: timeout après %s polls | deployment_id=%s",
        step,
        poll,
        deployment_id,
    )
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
    manifest_path = _manifest_path(path)
    _log_deploy_step(
        "0/5 deploy_start",
        "préparation",
        algo=HASH_ALGO_VERSION,
        project=project_name,
        digest=digest,
        manifest_path=manifest_path,
        html_bytes=len(body),
    )
    if CF_PAGES_DEBUG_PRINT:
        print(
            f"\n=== [CF-PAGES-DEBUG] 0/5 deploy_start | CF_PAGES_DEBUG_PRINT=True ===\n"
            f"project={project_name} digest={digest} manifest_path={manifest_path} "
            f"html_bytes={len(body)}\n",
            flush=True,
        )

    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=15.0)) as client:
        deploy_started = time.monotonic()
        try:
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
                manifest={manifest_path: digest},
            )
            live_url = await _wait_deployment_ready(
                client,
                account_id=account_id,
                api_token=api_token,
                project_name=project_name,
                deployment_id=deployment_id,
            )
        except CloudflarePagesError:
            logger.exception(
                "[Cloudflare Pages] deploy_standalone_html: échec après %.1fs | project=%s",
                time.monotonic() - deploy_started,
                project_name,
            )
            raise
        except Exception:
            logger.exception(
                "[Cloudflare Pages] deploy_standalone_html: erreur inattendue | project=%s",
                project_name,
            )
            raise

        if not live_url.startswith("http"):
            live_url = f"https://{project_name}.pages.dev"

        _log_deploy_step(
            "done",
            "déploiement terminé",
            project=project_name,
            deployment_id=deployment_id,
            url=live_url,
            total_ms=int((time.monotonic() - deploy_started) * 1000),
        )
    return CloudflareDeployResult(
        project_name=project_name,
        deployment_id=deployment_id,
        url=live_url.rstrip("/"),
    )

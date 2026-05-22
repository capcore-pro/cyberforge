"""
Déploiement HTML autonome sur Cloudflare Pages (Direct Upload API).
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import re
import secrets
import time
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

API_BASE = "https://api.cloudflare.com/client/v4"
CYBERFORGE_DEMOS_PROJECT = "cyberforge-demos"
# Version algorithme hash (Wrangler blake3) — visible dans les logs au reload.
HASH_ALGO_VERSION = "wrangler-blake3-b64-ext-v1"

_ROOT_STUB_HTML = (
    "<!DOCTYPE html><html lang=\"fr\"><head><meta charset=\"UTF-8\"/>"
    "<title>CyberForge Demos</title></head><body>"
    "<p>Démos client CyberForge — accès via lien partagé.</p></body></html>"
).encode("utf-8")
ROOT_STUB_ASSET_PATH = "index.html"
ROOT_STUB_MANIFEST_PATH = "/index.html"
REDIRECTS_ASSET_PATH = "_redirects"
REDIRECTS_MANIFEST_PATH = "/_redirects"
# Proxy interne (200) : évite le fallback SPA sur /index.html pour les chemins /d/{token}/.
_REDIRECTS_BODY = (
    b"/d/:token /u:token.html 200\n"
    b"/d/:token/ /u:token.html 200\n"
)
_VALID_MANIFEST_PATH = re.compile(
    r"^u[a-zA-Z0-9_-]+\.html$|^d/[a-zA-Z0-9_-]+/index\.html$"
)
# TEMP DEBUG — print() stderr vers console uvicorn (retirer après diagnostic).
CF_PAGES_DEBUG_PRINT = False

# Copie locale du dernier HTML envoyé à l'API upload Cloudflare (diagnostic).
LAST_CF_UPLOAD_HTML = Path(__file__).resolve().parent.parent / "_last_cf_upload.html"
LAST_CF_DEPLOY_MANIFEST = (
    Path(__file__).resolve().parent.parent / "_last_cf_deploy_manifest.json"
)

_HTML_MARKERS = (
    "cf-password-toggle",
    "cf-eye-on",
    "cf-lock-btn",
    "saas-menu-btn",
)


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
    asset_path: str | None = None
    content_hash: str | None = None


def pages_project_name_for_token(token: str) -> str:
    """Déprécié — toutes les démos utilisent CYBERFORGE_DEMOS_PROJECT."""
    return CYBERFORGE_DEMOS_PROJECT


def pages_token_slug(token: str) -> str:
    """Segment URL /d/{slug}/ — identique au token nettoyé (sans préfixe u)."""
    return re.sub(r"[^a-zA-Z0-9_-]", "", token.strip()) or "demo"


def pages_slug_for_token(token: str) -> str:
    """
    Nom de fichier plat (préfixe u) — évite un chemin manifest /-token.html
    que Pages/CDN route mal.
    """
    return f"u{pages_token_slug(token)}"


def pages_asset_path_for_token(token: str) -> str:
    """Chemin fichier principal (racine) — servi directement par Pages."""
    return f"{pages_slug_for_token(token)}.html"


def pages_asset_path_legacy_for_token(token: str) -> str:
    """Chemin /d/{token}/index.html — doit correspondre aux liens partagés."""
    return f"d/{pages_token_slug(token)}/index.html"


def pages_manifest_path_for_token(token: str) -> str:
    return _manifest_path(pages_asset_path_for_token(token))


def public_demo_url_for_token(token: str) -> str:
    """URL publique de la démo (fichier plat à la racine du projet Pages)."""
    base = f"https://{CYBERFORGE_DEMOS_PROJECT}.pages.dev"
    return f"{base}/{pages_asset_path_for_token(token)}"


def _root_stub_digest() -> str:
    return _file_digest(ROOT_STUB_ASSET_PATH, _ROOT_STUB_HTML)


def _redirects_digest() -> str:
    return _file_digest(REDIRECTS_ASSET_PATH, _REDIRECTS_BODY)


def apply_deploy_cache_bust(html: str) -> str:
    """
    Injecte un marqueur unique pour forcer un nouveau hash Cloudflare à chaque déploiement.

    Sans cela, un HTML identique réutilise le même digest et Pages peut servir un asset en cache.
    """
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%f")[:-3] + "Z"
    nonce = secrets.token_hex(6)
    marker = f"<!-- cf-deploy:{stamp}:{nonce} -->"
    lower = html.lower()
    end = lower.rfind("</html>")
    if end >= 0:
        return html[:end] + marker + html[end:]
    return html + marker


def _html_marker_report(html: str) -> dict[str, bool]:
    return {name: name in html for name in _HTML_MARKERS}


def _log_upload_html_snapshot(
    *,
    asset_path: str,
    html: str,
    digest: str,
    manifest_path: str,
) -> None:
    """Journalise et sauvegarde le HTML exact uploadé vers Cloudflare."""
    encoded = html.encode("utf-8")
    markers = _html_marker_report(html)
    logger.info(
        "[Cloudflare Pages] upload_html | path=%s | manifest=%s | digest=%s | bytes=%s | markers=%s",
        asset_path,
        manifest_path,
        digest,
        len(encoded),
        markers,
    )
    for name, present in markers.items():
        if not present:
            logger.warning(
                "[Cloudflare Pages] upload_html: marqueur ABSENT — %s", name
            )
    for needle in ("cf-password-toggle", "cf-lock-btn"):
        idx = html.find(needle)
        if idx >= 0:
            snippet = html[max(0, idx - 60) : idx + 140].replace("\n", " ")
            logger.info(
                "[Cloudflare Pages] upload_html snippet | %s | …%s…",
                needle,
                snippet,
            )
    try:
        LAST_CF_UPLOAD_HTML.write_text(html, encoding="utf-8")
        logger.info(
            "[Cloudflare Pages] upload_html sauvegardé | file=%s",
            LAST_CF_UPLOAD_HTML,
        )
    except OSError as exc:
        logger.warning(
            "[Cloudflare Pages] impossible d'écrire %s: %s",
            LAST_CF_UPLOAD_HTML,
            exc,
        )


def demo_content_digest(token: str, html: str) -> tuple[str, str]:
    """Retourne (chemin asset, hash) pour persistance Supabase."""
    asset_path = pages_asset_path_for_token(token)
    return asset_path, _file_digest(asset_path, html.encode("utf-8"))


def sanitize_manifest_entries(entries: dict[str, str]) -> dict[str, str]:
    """Ne garde que les chemins démo valides (évite entrées Supabase obsolètes)."""
    cleaned: dict[str, str] = {}
    for path, digest in entries.items():
        if path == ROOT_STUB_ASSET_PATH:
            continue
        if not isinstance(path, str) or not isinstance(digest, str):
            continue
        p = path.strip()
        d = digest.strip()
        if not p or not d:
            continue
        if _VALID_MANIFEST_PATH.match(p):
            cleaned[p] = d
    return cleaned


def build_pages_manifest(
    entries: dict[str, str],
    *,
    include_root_stub: bool = False,
) -> dict[str, str]:
    """Manifest : redirects + entrées démo ; stub racine optionnel (désactivé par défaut)."""
    manifest: dict[str, str] = {REDIRECTS_MANIFEST_PATH: _redirects_digest()}
    if include_root_stub:
        manifest[ROOT_STUB_MANIFEST_PATH] = _root_stub_digest()
    for path, digest in entries.items():
        manifest[_manifest_path(path)] = digest
    return manifest


def _save_deploy_manifest_snapshot(
    *,
    token: str,
    manifest: dict[str, str],
    upload_files: dict[str, bytes],
    asset_path: str,
    legacy_path: str,
    digest: str,
) -> None:
    """Persiste le manifest exact + métadonnées du dernier déploiement (diagnostic)."""
    upload_meta: dict[str, dict[str, object]] = {}
    for path, body in upload_files.items():
        manifest_key = _manifest_path(path)
        expected = _file_digest(path, body)
        upload_meta[path] = {
            "manifest_key": manifest_key,
            "bytes": len(body),
            "digest_computed": expected,
            "digest_in_manifest": manifest.get(manifest_key),
            "manifest_match": manifest.get(manifest_key) == expected,
        }
    payload = {
        "token": token,
        "slug": pages_slug_for_token(token),
        "token_slug": pages_token_slug(token),
        "primary_asset_path": asset_path,
        "legacy_asset_path": legacy_path,
        "primary_digest": digest,
        "public_url": public_demo_url_for_token(token),
        "manifest": manifest,
        "upload_files": sorted(upload_files.keys()),
        "upload_meta": upload_meta,
    }
    manifest_json = json.dumps(manifest, indent=2, ensure_ascii=False)
    logger.info(
        "[Cloudflare Pages] manifest déploiement | token=%s | paths=%s | json=%s",
        token,
        sorted(manifest.keys()),
        manifest_json,
    )
    try:
        LAST_CF_DEPLOY_MANIFEST.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info(
            "[Cloudflare Pages] manifest sauvegardé | file=%s",
            LAST_CF_DEPLOY_MANIFEST,
        )
    except OSError as exc:
        logger.warning(
            "[Cloudflare Pages] impossible d'écrire %s: %s",
            LAST_CF_DEPLOY_MANIFEST,
            exc,
        )


def build_deploy_zip(files: dict[str, bytes]) -> bytes:
    """Archive ZIP en mémoire pour Direct Upload (u{token}.html + _redirects, etc.)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.writestr(path, files[path])
    return buf.getvalue()


def zip_contains_marker(zip_bytes: bytes, marker: str = "cf-password-toggle") -> bool:
    """Vérifie qu'une archive de déploiement contient le marqueur dans un fichier HTML."""
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
            for name in archive.namelist():
                if not name.lower().endswith(".html"):
                    continue
                body = archive.read(name).decode("utf-8", errors="replace")
                if marker in body:
                    logger.info(
                        "[Cloudflare Pages] ZIP OK | file=%s | marker=%s | bytes=%s",
                        name,
                        marker,
                        len(body.encode("utf-8")),
                    )
                    return True
    except zipfile.BadZipFile as exc:
        logger.error("[Cloudflare Pages] ZIP invalide : %s", exc)
        return False
    logger.error(
        "[Cloudflare Pages] ZIP sans marqueur %s | entries=%s",
        marker,
        [
            n
            for n in zipfile.ZipFile(io.BytesIO(zip_bytes)).namelist()
            if n.endswith(".html")
        ],
    )
    return False


def files_from_deploy_zip(zip_bytes: bytes) -> dict[str, bytes]:
    """Extrait les fichiers d'une archive de déploiement."""
    out: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        for name in archive.namelist():
            if name.endswith("/"):
                continue
            out[name] = archive.read(name)
    return out


def _content_type_for_asset(path: str) -> str:
    if path == REDIRECTS_ASSET_PATH:
        return "text/plain; charset=utf-8"
    if path.endswith(".html"):
        return "text/html; charset=utf-8"
    return "application/octet-stream"


def _validate_manifest_covers_uploads(
    manifest: dict[str, str],
    upload_files: dict[str, bytes],
) -> None:
    """Vérifie que chaque fichier uploadé est référencé avec le bon hash dans le manifest."""
    for path, body in upload_files.items():
        manifest_key = _manifest_path(path)
        expected = _file_digest(path, body)
        actual = manifest.get(manifest_key)
        if actual != expected:
            raise CloudflarePagesError(
                f"Manifest incohérent pour {manifest_key}: "
                f"attendu {expected}, manifest {actual!r}."
            )
    primary_html_paths = [
        p for p in upload_files if p.endswith(".html") and p != ROOT_STUB_ASSET_PATH
    ]
    if not primary_html_paths:
        return
    for path in primary_html_paths:
        if manifest.get(_manifest_path(path)) is None:
            raise CloudflarePagesError(
                f"Fichier {path} uploadé mais absent du manifest de déploiement."
            )


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


async def _upload_assets_batch(
    client: httpx.AsyncClient,
    *,
    upload_jwt: str,
    manifest: dict[str, str],
    upload_files: dict[str, bytes],
) -> None:
    """Envoie tous les fichiers du ZIP en un seul POST /pages/assets/upload."""
    step = "3/5 upload_zip_assets"
    url = f"{API_BASE}/pages/assets/upload"
    payload: list[dict[str, object]] = []
    for path, body in upload_files.items():
        manifest_key = _manifest_path(path)
        digest = manifest.get(manifest_key) or _file_digest(path, body)
        payload.append(
            {
                "key": digest,
                "value": base64.b64encode(body).decode("ascii"),
                "metadata": {"contentType": _content_type_for_asset(path)},
                "base64": True,
            }
        )
    if not payload:
        return
    _log_deploy_step(
        step,
        "début POST batch",
        file_count=len(payload),
        paths=sorted(upload_files.keys()),
        zip_bytes=sum(len(b) for b in upload_files.values()),
        url=url,
    )
    started = time.monotonic()
    resp = await client.post(
        url,
        headers={"Authorization": f"Bearer {upload_jwt}"},
        json=payload,
    )
    elapsed_ms = int((time.monotonic() - started) * 1000)
    result = _check_response(resp, "upload_assets_batch")
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
    zip_bytes: bytes | None = None,
) -> str:
    """
    Crée le déploiement (Direct Upload) avec archive ZIP + manifest.

    Le manifest est envoyé en multipart/form-data (comme Wrangler).
    """
    url = (
        f"{API_BASE}/accounts/{account_id}/pages/projects/"
        f"{project_name}/deployments"
    )
    step = "4/5 create_deployment"
    manifest_json = json.dumps(manifest)
    multipart_files: dict[str, tuple] = {
        "manifest": (None, manifest_json, "application/json"),
    }
    if zip_bytes:
        multipart_files["file"] = ("deployment.zip", zip_bytes, "application/zip")
    _log_deploy_step(
        step,
        "début POST multipart",
        project=project_name,
        manifest=manifest,
        manifest_bytes=len(manifest_json.encode("utf-8")),
        zip_bytes=len(zip_bytes) if zip_bytes else 0,
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
            "zip_bytes": len(zip_bytes) if zip_bytes else 0,
        },
    )
    resp = await client.post(
        url,
        headers=_api_headers(api_token),
        files=multipart_files,
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


async def _deploy_with_manifest(
    *,
    account_id: str,
    api_token: str,
    project_name: str,
    manifest: dict[str, str],
    upload_files: dict[str, bytes],
) -> CloudflareDeployResult:
    """Direct Upload : ZIP en mémoire → batch upload assets → déploiement multipart."""
    files = dict(upload_files)
    if REDIRECTS_ASSET_PATH not in files:
        files[REDIRECTS_ASSET_PATH] = _REDIRECTS_BODY

    zip_bytes = build_deploy_zip(files)
    if not zip_contains_marker(zip_bytes, "cf-password-toggle"):
        raise CloudflarePagesError(
            "ZIP de déploiement sans cf-password-toggle — déploiement annulé."
        )
    _log_deploy_step(
        "0/5 deploy_start",
        "préparation ZIP",
        algo=HASH_ALGO_VERSION,
        project=project_name,
        manifest_paths=len(manifest),
        upload_count=len(files),
        zip_bytes=len(zip_bytes),
        zip_entries=sorted(files.keys()),
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
            for asset_path, body in files.items():
                if not (asset_path.endswith(".html") or "index.html" in asset_path):
                    continue
                manifest_key = _manifest_path(asset_path)
                digest = manifest.get(manifest_key) or _file_digest(asset_path, body)
                try:
                    html_text = body.decode("utf-8")
                    _log_upload_html_snapshot(
                        asset_path=asset_path,
                        html=html_text,
                        digest=digest,
                        manifest_path=manifest_key,
                    )
                except UnicodeDecodeError:
                    logger.warning(
                        "[Cloudflare Pages] upload %s: corps non UTF-8",
                        asset_path,
                    )
            await _upload_assets_batch(
                client,
                upload_jwt=upload_jwt,
                manifest=manifest,
                upload_files=files,
            )
            unique_digests = sorted(set(manifest.values()))
            if unique_digests:
                await _upsert_hashes(client, upload_jwt=upload_jwt, digests=unique_digests)
            deployment_id = await _create_deployment(
                client,
                account_id=account_id,
                api_token=api_token,
                project_name=project_name,
                manifest=manifest,
                zip_bytes=zip_bytes,
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
                "[Cloudflare Pages] deploy: échec après %.1fs | project=%s",
                time.monotonic() - deploy_started,
                project_name,
            )
            raise
        except Exception:
            logger.exception(
                "[Cloudflare Pages] deploy: erreur inattendue | project=%s",
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
        asset_path=None,
        content_hash=None,
    )


async def deploy_demo_to_cyberforge_demos(
    *,
    account_id: str,
    api_token: str,
    token: str,
    html: str,
    other_manifest_entries: dict[str, str],
) -> CloudflareDeployResult:
    """
    Publie la démo sous /d/{token}/ sur le projet fixe cyberforge-demos.
    other_manifest_entries : chemins actifs path relatif → hash (hors cette démo).
    """
    asset_path = pages_asset_path_for_token(token)
    html_fresh = apply_deploy_cache_bust(html)
    body = html_fresh.encode("utf-8")
    digest = _file_digest(asset_path, body)
    manifest_path = _manifest_path(asset_path)
    _log_upload_html_snapshot(
        asset_path=asset_path,
        html=html_fresh,
        digest=digest,
        manifest_path=manifest_path,
    )
    entries = sanitize_manifest_entries(other_manifest_entries)
    entries[asset_path] = digest
    manifest = build_pages_manifest(entries, include_root_stub=False)
    _log_deploy_step(
        "0/5 deploy_demo",
        "ZIP Direct Upload (cache-bust actif)",
        asset_path=asset_path,
        digest=digest,
        manifest_paths=sorted(manifest.keys()),
        manifest_entry=manifest.get(manifest_path),
    )
    upload_files = {
        asset_path: body,
        REDIRECTS_ASSET_PATH: _REDIRECTS_BODY,
    }

    if "cf-password-toggle" not in html_fresh:
        raise CloudflarePagesError(
            "HTML de démo sans cf-password-toggle avant déploiement Cloudflare."
        )

    pre_zip = build_deploy_zip(upload_files)
    if not zip_contains_marker(pre_zip, "cf-password-toggle"):
        raise CloudflarePagesError(
            "ZIP pré-upload sans cf-password-toggle — vérifiez wrap_with_password_gate."
        )
    logger.info(
        "[Cloudflare Pages] deploy_demo ZIP validé | token=%s | zip_bytes=%s | toggle=True",
        token,
        len(pre_zip),
    )

    _validate_manifest_covers_uploads(manifest, upload_files)
    _save_deploy_manifest_snapshot(
        token=token,
        manifest=manifest,
        upload_files=upload_files,
        asset_path=asset_path,
        legacy_path="",
        digest=digest,
    )

    result = await _deploy_with_manifest(
        account_id=account_id,
        api_token=api_token,
        project_name=CYBERFORGE_DEMOS_PROJECT,
        manifest=manifest,
        upload_files=upload_files,
    )
    live_url = public_demo_url_for_token(token)
    await _verify_deployed_demo_live(live_url)
    return CloudflareDeployResult(
        project_name=result.project_name,
        deployment_id=result.deployment_id,
        url=live_url,
        asset_path=asset_path,
        content_hash=digest,
    )


async def _verify_deployed_demo_live(url: str) -> None:
    """
    Vérifie que Pages sert bien le HTML démo (pas le stub index.html).

    Si le chemin manifest ne correspond pas à l'URL publique, Pages renvoie
    le stub racine (~179 octets, sans cf-password-toggle).
    """
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
    except httpx.HTTPError as exc:
        logger.warning(
            "[Cloudflare Pages] verify_live: requête impossible | url=%s | err=%s",
            url,
            exc,
        )
        return

    body = resp.text
    size = len(resp.content)
    has_toggle = "cf-password-toggle" in body
    is_stub = "CyberForge Demos" in body and size < 600
    logger.info(
        "[Cloudflare Pages] verify_live | url=%s | status=%s | bytes=%s | "
        "toggle=%s | stub=%s",
        url,
        resp.status_code,
        size,
        has_toggle,
        is_stub,
    )
    if resp.status_code != 200:
        logger.error(
            "[Cloudflare Pages] verify_live: HTTP %s pour %s",
            resp.status_code,
            url,
        )
        return
    if is_stub or not has_toggle:
        msg = (
            f"Cloudflare sert le stub ou un HTML incomplet ({url}, {size} octets). "
            "Recréez la démo après redémarrage du backend."
        )
        logger.error("[Cloudflare Pages] verify_live: %s", msg)
        raise CloudflarePagesError(msg)


async def remove_demo_from_cyberforge_demos(
    *,
    account_id: str,
    api_token: str,
    remaining_manifest_entries: dict[str, str],
) -> CloudflareDeployResult:
    """Retire une démo du manifest (lien 404) sans re-uploader son HTML."""
    manifest = build_pages_manifest(
        sanitize_manifest_entries(remaining_manifest_entries),
        include_root_stub=False,
    )
    return await _deploy_with_manifest(
        account_id=account_id,
        api_token=api_token,
        project_name=CYBERFORGE_DEMOS_PROJECT,
        manifest=manifest,
        upload_files={},
    )


async def deploy_standalone_html(
    *,
    account_id: str,
    api_token: str,
    project_name: str,
    html: str,
) -> CloudflareDeployResult:
    """Compat — délègue au projet fixe si project_name est cyberforge-demos."""
    if project_name == CYBERFORGE_DEMOS_PROJECT:
        raise CloudflarePagesError(
            "Utilisez deploy_demo_to_cyberforge_demos avec un token de démo."
        )
    body = html.encode("utf-8")
    path = "index.html"
    digest = _file_digest(path, body)
    manifest = {_manifest_path(path): digest}
    return await _deploy_with_manifest(
        account_id=account_id,
        api_token=api_token,
        project_name=project_name,
        manifest=manifest,
        upload_files={path: body},
    )

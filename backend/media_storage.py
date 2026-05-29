"""
Stockage physique des assets médiathèque — disque local + sync Cloudflare R2.

Variables d'environnement (backend/.env et Railway) :
  CLOUDFLARE_R2_ACCOUNT_ID
  CLOUDFLARE_R2_ACCESS_KEY_ID
  CLOUDFLARE_R2_SECRET_ACCESS_KEY
  CLOUDFLARE_R2_BUCKET          (ex. cyberforge-media)
  CLOUDFLARE_R2_PUBLIC_BASE_URL (optionnel, URL publique du bucket — ex. https://media.example.com)
  MEDIA_ROOT                    (optionnel, défaut : <repo>/media/)
"""

from __future__ import annotations

import logging
import mimetypes
import os
import re
import uuid
from pathlib import Path
from typing import Any, Literal

from config import get_settings, plain_secret_str
from media_db import update_asset_r2

logger = logging.getLogger(__name__)

MediaTypeArg = Literal["image", "zip", "pdf"]

_TYPE_SUBDIRS: dict[str, str] = {
    "image": "images",
    "zip": "zips",
    "pdf": "pdfs",
}

# Défaut : C:/Users/mathi/cyberforge/media/ lorsque le dépôt est cyberforge
_DEFAULT_MEDIA_ROOT = Path(__file__).resolve().parent.parent / "media"


def media_root() -> Path:
    """Racine du stockage local (créée à la demande)."""
    raw = os.environ.get("MEDIA_ROOT", "").strip()
    if not raw:
        settings = get_settings()
        raw = (getattr(settings, "media_root", None) or "").strip()
    root = Path(raw).expanduser().resolve() if raw else _DEFAULT_MEDIA_ROOT.resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _ensure_type_dir(media_type: MediaTypeArg) -> Path:
    key = media_type.strip().lower()
    if key not in _TYPE_SUBDIRS:
        raise ValueError("type doit être image, zip ou pdf.")
    directory = media_root() / _TYPE_SUBDIRS[key]
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _sanitize_filename(filename: str) -> str:
    base = Path(filename).name.strip()
    safe = re.sub(r"[^\w.\- ]+", "_", base, flags=re.UNICODE).strip()
    return safe or "file"


def save_local(file_bytes: bytes, filename: str, type: MediaTypeArg) -> str:
    """
    Enregistre un fichier sous media/{images|zips|pdfs}/.
    Retourne le chemin absolu sur disque.
    """
    if not file_bytes:
        raise ValueError("file_bytes vide.")
    directory = _ensure_type_dir(type)
    safe_name = _sanitize_filename(filename)
    unique_name = f"{uuid.uuid4().hex[:12]}_{safe_name}"
    target = (directory / unique_name).resolve()
    target.write_bytes(file_bytes)
    return str(target)


def delete_local(local_path: str) -> bool:
    """Supprime le fichier local s'il existe (ne lève pas si absent)."""
    try:
        path = Path(local_path).resolve()
        if path.is_file():
            path.unlink()
            return True
    except OSError as exc:
        logger.warning("delete_local(%s): %s", local_path, exc)
    return False


def get_local_url(local_path: str) -> str:
    """
    URL relative servie par FastAPI : /api/media/files/{id}.
    Résout l'id via la table media_assets (local_path exact ou résolu).
    """
    from cockpit_db import _connect, _lock

    resolved = str(Path(local_path).resolve())
    raw = local_path.strip()

    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                """
                SELECT id FROM media_assets
                WHERE local_path = ? OR local_path = ?
                LIMIT 1
                """,
                (resolved, raw),
            ).fetchone()
        finally:
            conn.close()

    if row is None:
        raise FileNotFoundError(
            f"Aucun asset en base pour local_path={local_path!r}"
        )
    asset_id = str(row[0])
    return f"/api/media/files/{asset_id}"


def _r2_config() -> dict[str, str] | None:
    settings = get_settings()
    account_id = plain_secret_str(settings.cloudflare_r2_account_id)
    access_key = plain_secret_str(settings.cloudflare_r2_access_key_id)
    secret_key = plain_secret_str(settings.cloudflare_r2_secret_access_key)
    bucket = (settings.cloudflare_r2_bucket or "").strip()
    if not all([account_id, access_key, secret_key, bucket]):
        return None
    public_base = (settings.cloudflare_r2_public_base_url or "").strip()
    return {
        "account_id": account_id,
        "access_key": access_key,
        "secret_key": secret_key,
        "bucket": bucket,
        "public_base": public_base.rstrip("/"),
        "endpoint": f"https://{account_id}.r2.cloudflarestorage.com",
    }


def r2_configured() -> bool:
    return _r2_config() is not None


def _s3_client():
    cfg = _r2_config()
    if cfg is None:
        return None, None
    try:
        import boto3
        from botocore.config import Config
    except ImportError:
        logger.warning("boto3 absent — sync R2 désactivée (pip install boto3).")
        return None, None

    client = boto3.client(
        "s3",
        endpoint_url=cfg["endpoint"],
        aws_access_key_id=cfg["access_key"],
        aws_secret_access_key=cfg["secret_key"],
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )
    return client, cfg


def _public_r2_url(r2_key: str, cfg: dict[str, str]) -> str:
    key = r2_key.lstrip("/")
    if cfg.get("public_base"):
        return f"{cfg['public_base']}/{key}"
    # Sans domaine public configuré, URL path-style (accès selon politique bucket)
    return f"{cfg['endpoint']}/{cfg['bucket']}/{key}"


def sync_to_r2(local_path: str, r2_key: str) -> str | None:
    """
    Upload vers R2. Retourne l'URL publique ou None si R2 indisponible / erreur.
    """
    client, cfg = _s3_client()
    if client is None or cfg is None:
        logger.warning("R2 non configuré — sync ignorée (%s)", r2_key)
        return None

    path = Path(local_path)
    if not path.is_file():
        logger.warning("sync_to_r2 : fichier absent %s", local_path)
        return None

    clean_key = r2_key.strip().lstrip("/")
    if not clean_key:
        logger.warning("sync_to_r2 : r2_key vide")
        return None

    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    try:
        client.upload_file(
            str(path),
            cfg["bucket"],
            clean_key,
            ExtraArgs={"ContentType": content_type},
        )
        url = _public_r2_url(clean_key, cfg)
        logger.info("R2 sync OK : %s → %s", clean_key, url)
        return url
    except Exception as exc:
        logger.warning("Échec upload R2 (%s): %s", clean_key, exc)
        return None


def delete_from_r2(r2_key: str) -> bool:
    """Supprime un objet R2 ; False si non configuré ou erreur."""
    client, cfg = _s3_client()
    if client is None or cfg is None:
        logger.warning("R2 non configuré — delete ignoré (%s)", r2_key)
        return False

    clean_key = r2_key.strip().lstrip("/")
    if not clean_key:
        return False

    try:
        client.delete_object(Bucket=cfg["bucket"], Key=clean_key)
        return True
    except Exception as exc:
        logger.warning("Échec suppression R2 (%s): %s", clean_key, exc)
        return False


def _list_assets_pending_r2(limit: int = 500) -> list[dict[str, Any]]:
    from cockpit_db import _connect, _lock, _rows_to_dicts

    safe_limit = max(1, min(int(limit), 2000))
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM media_assets
                WHERE r2_url IS NULL
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
            assets = _rows_to_dicts(rows)
        finally:
            conn.close()

    for item in assets:
        if isinstance(item.get("tags"), str):
            try:
                import json

                item["tags"] = json.loads(item["tags"])
            except json.JSONDecodeError:
                item["tags"] = []
    return assets


def default_r2_key(asset: dict[str, Any]) -> str:
    """Clé S3 par défaut : {type}s/{id}/{filename}."""
    media_type = str(asset.get("type") or "image")
    sub = _TYPE_SUBDIRS.get(media_type, "images")
    aid = str(asset["id"])
    filename = _sanitize_filename(str(asset.get("filename") or "file"))
    return f"{sub}/{aid}/{filename}"


def sync_all_pending() -> dict[str, Any]:
    """
    Sync tous les assets sans r2_url dont le fichier local existe.
    Met à jour media_db (r2_url, r2_key) en cas de succès.
    """
    pending = _list_assets_pending_r2()
    synced: list[str] = []
    skipped: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []

    for asset in pending:
        aid = str(asset["id"])
        local_path = str(asset.get("local_path") or "")
        if not local_path or not Path(local_path).is_file():
            skipped.append({"asset_id": aid, "reason": "local_file_missing"})
            continue

        r2_key = (asset.get("r2_key") or "").strip() or default_r2_key(asset)
        url = sync_to_r2(local_path, r2_key)
        if not url:
            errors.append({"asset_id": aid, "reason": "r2_upload_failed"})
            continue

        try:
            updated = update_asset_r2(aid, url, r2_key)
            if updated is None:
                errors.append({"asset_id": aid, "reason": "db_update_failed"})
            else:
                synced.append(aid)
        except Exception as exc:
            logger.warning("update_asset_r2(%s): %s", aid, exc)
            errors.append({"asset_id": aid, "reason": str(exc)})

    return {
        "synced": synced,
        "skipped": skipped,
        "errors": errors,
        "count": len(synced),
    }

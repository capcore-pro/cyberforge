"""
Génération d'applications desktop (.exe) depuis des templates Electron.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from desktop_app_db import get_order, update_order
from media_storage import sync_to_r2

logger = logging.getLogger(__name__)

_BACKEND = Path(__file__).resolve().parent
_REPO_ROOT = _BACKEND.parent
_TEMPLATES_DIR = _BACKEND / "desktop_templates"
_TEMP_BUILDS_DIR = _BACKEND / "temp_builds"
_DESKTOP_APPS_DIR = _REPO_ROOT / "desktop_apps"

_TEXT_SUFFIXES = {".json", ".html", ".js", ".css", ".md"}
_APP_TITLES: dict[str, str] = {
    "facture_express": "Facture Express",
    "lead_tracker": "Lead Tracker",
    "caisse": "Caisse CapCore",
}


class DesktopAppGeneratorError(Exception):
    """Erreur de génération ou de publication desktop."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


def _expires_at_iso() -> str:
    return (_utc_now() + timedelta(days=7)).isoformat()


def _ensure_node_toolchain() -> tuple[str, str]:
    node = shutil.which("node")
    npm = shutil.which("npm")
    if not node:
        raise DesktopAppGeneratorError(
            "Node.js est requis pour compiler les applications desktop (introuvable dans le PATH)."
        )
    if not npm:
        raise DesktopAppGeneratorError(
            "npm est requis pour compiler les applications desktop (introuvable dans le PATH)."
        )
    try:
        version = subprocess.run(
            [node, "--version"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        logger.info("Node.js détecté : %s", (version.stdout or "").strip())
    except (subprocess.SubprocessError, OSError) as exc:
        raise DesktopAppGeneratorError(f"Impossible d'exécuter Node.js : {exc}") from exc
    return node, npm


def _placeholder_values(order: dict[str, Any]) -> dict[str, str]:
    app_type = str(order.get("app_type") or "").strip()
    order_id = str(order.get("id") or "").strip()
    client_name = (order.get("client_name") or "").strip() or "Client"
    app_title = _APP_TITLES.get(app_type, app_type.replace("_", " ").title())
    return {
        "{{CLIENT_NAME}}": client_name,
        "{{APP_TITLE}}": app_title,
        "{{ORDER_ID}}": order_id,
    }


def _personalize_tree(build_dir: Path, placeholders: dict[str, str]) -> None:
    for path in build_dir.rglob("*"):
        if not path.is_file():
            continue
        if "node_modules" in path.parts:
            continue
        if path.suffix.lower() not in _TEXT_SUFFIXES:
            continue
        try:
            original = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        updated = original
        for key, value in placeholders.items():
            updated = updated.replace(key, value)
        if updated != original:
            path.write_text(updated, encoding="utf-8")


def _copy_template(app_type: str, order_id: str) -> Path:
    src = _TEMPLATES_DIR / app_type
    if not src.is_dir():
        raise DesktopAppGeneratorError(f"Template introuvable : {app_type}")

    _TEMP_BUILDS_DIR.mkdir(parents=True, exist_ok=True)
    dest = _TEMP_BUILDS_DIR / order_id
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(
        src,
        dest,
        ignore=shutil.ignore_patterns("node_modules", "dist", ".git"),
    )
    return dest


def _run_npm(npm: str, args: list[str], cwd: Path, *, timeout: float | None = 900) -> None:
    cmd = [npm, *args]
    logger.info("npm %s (cwd=%s)", " ".join(args), cwd)
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise DesktopAppGeneratorError(
            f"Délai dépassé : npm {' '.join(args)}"
        ) from exc
    except OSError as exc:
        raise DesktopAppGeneratorError(f"Échec npm {' '.join(args)} : {exc}") from exc

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        stdout = (completed.stdout or "").strip()
        detail = stderr or stdout or f"code {completed.returncode}"
        raise DesktopAppGeneratorError(f"npm {' '.join(args)} a échoué : {detail}")


def _find_built_exe(dist_dir: Path) -> Path:
    if not dist_dir.is_dir():
        raise DesktopAppGeneratorError(f"Dossier dist absent : {dist_dir}")

    top_level = [p for p in dist_dir.glob("*.exe") if p.is_file()]
    if top_level:
        return max(top_level, key=lambda p: p.stat().st_mtime)

    exes = [p for p in dist_dir.rglob("*.exe") if p.is_file()]
    if not exes:
        raise DesktopAppGeneratorError("Aucun fichier .exe produit par Electron Builder.")

    named = [p for p in exes if p.name.lower() != "electron.exe"]
    pool = named or exes
    return max(pool, key=lambda p: p.stat().st_mtime)


def _safe_filename(name: str) -> str:
    base = re.sub(r"[^\w.\-]+", "_", name.strip())[:80]
    return base or "app"


def _publish_exe(order_id: str, app_type: str, built_exe: Path) -> tuple[Path, str | None]:
    out_dir = _DESKTOP_APPS_DIR / order_id
    out_dir.mkdir(parents=True, exist_ok=True)
    dest_name = f"{_safe_filename(app_type)}_{order_id[:8]}.exe"
    dest_path = out_dir / dest_name
    shutil.copy2(built_exe, dest_path)

    r2_key = f"desktop-apps/{order_id}/{dest_name}"
    r2_url = sync_to_r2(str(dest_path), r2_key)
    return dest_path, r2_url


def _build_and_publish(order: dict[str, Any]) -> str:
    order_id = str(order["id"])
    app_type = str(order["app_type"]).strip()

    _, npm = _ensure_node_toolchain()

    build_dir = _copy_template(app_type, order_id)
    placeholders = _placeholder_values(order)
    _personalize_tree(build_dir, placeholders)

    _run_npm(npm, ["install"], build_dir, timeout=600)
    _run_npm(npm, ["run", "build"], build_dir, timeout=900)

    built_exe = _find_built_exe(build_dir / "dist")
    exe_path, r2_url = _publish_exe(order_id, app_type, built_exe)

    if not r2_url:
        raise DesktopAppGeneratorError(
            "Compilation réussie mais upload R2 indisponible — vérifiez CLOUDFLARE_R2_*."
        )

    updated = update_order(
        order_id,
        generation_status="ready",
        exe_path=str(exe_path),
        r2_url=r2_url,
        expires_at=_expires_at_iso(),
    )
    if updated is None:
        logger.warning("Commande %s introuvable après build", order_id)

    logger.info(
        "Desktop app prête — order=%s type=%s exe=%s r2=%s",
        order_id,
        app_type,
        exe_path,
        r2_url,
    )
    return r2_url


def generate_exe(order_id: str) -> str:
    """
    Génère un .exe personnalisé pour la commande et publie sur R2.

    Retourne l'URL publique R2. En cas d'échec, met generation_status à failed
    et lève DesktopAppGeneratorError (sans laisser remonter une exception non gérée).
    """
    oid = order_id.strip()
    if not oid:
        raise DesktopAppGeneratorError("order_id requis.")

    order = get_order(oid)
    if order is None:
        raise DesktopAppGeneratorError(f"Commande introuvable : {oid}")

    app_type = str(order.get("app_type") or "").strip()
    if app_type not in _APP_TITLES:
        raise DesktopAppGeneratorError(f"Type d'application non supporté : {app_type}")

    update_order(oid, generation_status="generating")

    try:
        return _build_and_publish(order)
    except Exception as exc:
        logger.exception("Génération desktop échouée — order_id=%s", oid)
        update_order(oid, generation_status="failed")
        if isinstance(exc, DesktopAppGeneratorError):
            raise
        raise DesktopAppGeneratorError(str(exc)) from exc

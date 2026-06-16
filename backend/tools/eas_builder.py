"""
EAS Builder — génération structure Expo, configuration EAS et builds Android APK.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import httpx

from config import get_settings, plain_secret_str

logger = logging.getLogger(__name__)

EAS_API_BASE = "https://api.expo.dev/v2"


class EasBuilderError(Exception):
    """Erreur lors d'une opération EAS Builder."""


def get_build_root(app_id: str) -> Path:
    """Répertoire de build pour une app mobile."""
    base = Path(os.getenv("MOBILE_BUILD_ROOT", tempfile.gettempdir())) / "mobile_builds"
    root = base / app_id
    root.mkdir(parents=True, exist_ok=True)
    return root


def _expo_token() -> str:
    settings = get_settings()
    token = (
        os.getenv("EXPO_TOKEN", "").strip()
        or plain_secret_str(getattr(settings, "expo_token", None))
    )
    if not token:
        raise EasBuilderError(
            "EXPO_TOKEN non configuré. Connectez EAS CLI ou définissez la variable d'environnement."
        )
    return token


def generate_app_structure(app_config: dict[str, Any], files: dict[str, str]) -> Path:
    """
    Écrit les fichiers générés par MobileAI dans le répertoire de build.
    Retourne le chemin racine du projet.
    """
    app_id = str(app_config.get("id") or "").strip()
    if not app_id:
        raise EasBuilderError("app_config.id requis.")
    root = get_build_root(app_id)
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)

    for rel_path, content in files.items():
        dest = root / rel_path.replace("\\", "/")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")

    assets_dir = root / "assets"
    assets_dir.mkdir(exist_ok=True)
    placeholder_icon = assets_dir / "icon.png"
    if not placeholder_icon.exists():
        # PNG 1x1 minimal (valide) si pas de logo
        placeholder_icon.write_bytes(
            bytes.fromhex(
                "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
                "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
            )
        )
    for name in ("splash-icon.png", "android-icon-foreground.png", "favicon.png"):
        target = assets_dir / name
        if not target.exists() and placeholder_icon.exists():
            shutil.copy(placeholder_icon, target)

    return root


def configure_eas(app_id: str, bundle_id: str, app_config: dict[str, Any]) -> dict[str, str]:
    """Génère eas.json et app.json dans le répertoire de build."""
    root = get_build_root(app_id)
    name = str(app_config.get("name") or "App")
    slug = str(app_config.get("app_slug") or app_id[:8])
    primary = str(app_config.get("primary_color") or "#06b6d4")
    features = app_config.get("features") or []
    if isinstance(features, str):
        features = json.loads(features) if features else []

    plugins: list[Any] = ["expo-router"]
    if "push_notifications" in features:
        plugins.append(
            [
                "expo-notifications",
                {"icon": "./assets/notification-icon.png", "color": primary},
            ]
        )
    if "camera" in features:
        plugins.append(
            [
                "expo-camera",
                {"cameraPermission": "Autoriser l'accès à la caméra."},
            ]
        )
    if "geolocation" in features:
        plugins.append(
            [
                "expo-location",
                {
                    "locationAlwaysAndWhenInUsePermission": (
                        "Autoriser la géolocalisation pour cette application."
                    ),
                },
            ]
        )

    app_json = {
        "expo": {
            "name": name,
            "slug": slug,
            "version": "1.0.0",
            "orientation": "portrait",
            "icon": "./assets/icon.png",
            "scheme": re.sub(r"[^a-z0-9]", "", slug.lower())[:20] or "app",
            "userInterfaceStyle": "dark",
            "splash": {
                "image": "./assets/splash-icon.png",
                "resizeMode": "contain",
                "backgroundColor": primary,
            },
            "android": {
                "adaptiveIcon": {
                    "foregroundImage": "./assets/android-icon-foreground.png",
                    "backgroundColor": primary,
                },
                "package": bundle_id or f"com.capcore.{slug.replace('-', '')}",
                "usesCleartextTraffic": True,
            },
            "plugins": plugins,
            "extra": {"router": {}},
            "owner": os.getenv("EXPO_OWNER", "cyberforge"),
        }
    }

    eas_json = {
        "cli": {"version": ">= 12.0.0", "appVersionSource": "remote"},
        "build": {
            "development": {
                "developmentClient": True,
                "distribution": "internal",
            },
            "preview": {
                "distribution": "internal",
                "android": {"buildType": "apk"},
            },
            "production": {
                "autoIncrement": True,
                "android": {"buildType": "apk"},
            },
        },
        "submit": {"production": {}},
    }

    app_path = root / "app.json"
    eas_path = root / "eas.json"
    app_path.write_text(json.dumps(app_json, indent=2, ensure_ascii=False), encoding="utf-8")
    eas_path.write_text(json.dumps(eas_json, indent=2, ensure_ascii=False), encoding="utf-8")

    return {"app.json": str(app_path), "eas.json": str(eas_path)}


async def trigger_eas_build(app_id: str, profile: str = "preview") -> str:
    """
    Lance eas build --platform android --non-interactive.
    Retourne l'identifiant EAS du build.
    """
    root = get_build_root(app_id)
    if not (root / "package.json").exists():
        raise EasBuilderError(f"Projet Expo introuvable pour {app_id}. Générez d'abord l'app.")

    token = _expo_token()
    env = {**os.environ, "EXPO_TOKEN": token}

    # Installation des dépendances si node_modules absent
    if not (root / "node_modules").exists():
        logger.info("Installation npm dans %s", root)
        npm = shutil.which("npm") or "npm"
        install = subprocess.run(
            [npm, "install", "--legacy-peer-deps"],
            cwd=str(root),
            env=env,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if install.returncode != 0:
            raise EasBuilderError(f"npm install échoué: {install.stderr or install.stdout}")

    eas_cmd = shutil.which("eas") or shutil.which("eas.cmd") or "eas"
    cmd = [
        eas_cmd,
        "build",
        "--platform",
        "android",
        "--non-interactive",
        "--profile",
        profile,
        "--json",
    ]
    logger.info("Lancement EAS build: %s (cwd=%s)", " ".join(cmd), root)
    proc = subprocess.run(
        cmd,
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    log_path = root / "eas-build.log"
    log_path.write_text(output, encoding="utf-8")

    if proc.returncode != 0:
        raise EasBuilderError(f"eas build a échoué: {output[-2000:]}")

    build_id = _extract_build_id(output)
    if not build_id:
        raise EasBuilderError("Impossible d'extraire eas_build_id depuis la sortie EAS.")
    return build_id


def _extract_build_id(output: str) -> str | None:
    """Extrait l'ID de build depuis la sortie JSON ou texte EAS CLI."""
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("{"):
            try:
                data = json.loads(line)
                if isinstance(data, dict):
                    bid = data.get("id") or data.get("buildId")
                    if bid:
                        return str(bid)
            except json.JSONDecodeError:
                pass
    match = re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", output)
    return match.group(0) if match else None


async def check_build_status(eas_build_id: str) -> dict[str, Any]:
    """
    Interroge l'API EAS pour le statut du build.
    Retourne status, apk_url (artifacts) si terminé.
    """
    token = _expo_token()
    url = f"{EAS_API_BASE}/builds/{eas_build_id}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            url,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
        if resp.status_code == 404:
            return {"status": "unknown", "apk_url": None, "message": "Build introuvable"}
        resp.raise_for_status()
        data = resp.json()

    status = str(data.get("status") or "unknown").lower()
    apk_url: str | None = None
    artifacts = data.get("artifacts") or {}
    if isinstance(artifacts, dict):
        apk_url = artifacts.get("buildUrl") or artifacts.get("applicationArchiveUrl")
    if not apk_url and isinstance(data.get("artifacts"), list):
        for art in data["artifacts"]:
            if isinstance(art, dict) and art.get("url"):
                apk_url = str(art["url"])
                break

    return {
        "status": status,
        "apk_url": apk_url,
        "platform": data.get("platform"),
        "error": data.get("error") or data.get("errorMessage"),
    }


async def download_apk(apk_url: str, app_id: str) -> Path:
    """Télécharge l'APK dans le répertoire de build."""
    if not apk_url:
        raise EasBuilderError("URL APK manquante.")
    root = get_build_root(app_id)
    dest = root / "app-release.apk"
    async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
        resp = await client.get(apk_url)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
    return dest

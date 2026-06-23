"""
ElectronCompiler — CyberForge
Pousse le code généré par ElectronAI sur GitHub et déclenche la compilation .exe.
Utilise un repo template capcore-pro/cyberforge-desktop-template.
Zéro SDK superflu — juste httpx.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import re
from typing import Any

import httpx

from config import get_settings, plain_secret_str

logger = logging.getLogger(__name__)

GITHUB_ORG = "capcore-pro"
TEMPLATE_REPO = "cyberforge-desktop-template"
GITHUB_API = "https://api.github.com"


class ElectronCompiler:
    """
    Gère le cycle complet de compilation .exe client :
    1. Crée un repo depuis le template
    2. Pousse le code ElectronAI dedans
    3. Déclenche GitHub Actions
    4. Poll le statut jusqu'au succès
    5. Retourne l'URL de téléchargement .exe
    """

    def __init__(self, token: str | None = None) -> None:
        self.token = (token or plain_secret_str(get_settings().github_token)).strip()
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def compile(
        self,
        app_name: str,
        client_name: str,
        files: dict[str, str],
        model: str = "one_shot",
        license_key: str = "",
        version: str = "1.0.0",
    ) -> dict[str, Any]:
        """
        Point d'entrée principal.
        files = dict retourné par electron_ai.py
        Retourne { repo, run_id, status, download_url }
        """
        repo_name = self._repo_name(client_name, app_name)

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                await self._create_repo_from_template(client, repo_name)
                logger.info("ElectronCompiler — repo créé : %s", repo_name)

                await asyncio.sleep(5)

                await self._push_files(
                    client, repo_name, files, model, license_key, version
                )
                logger.info(
                    "ElectronCompiler — fichiers poussés : %s fichiers", len(files)
                )

                run_id = await self._trigger_build(client, repo_name, version)
                logger.info("ElectronCompiler — build déclenché : run_id=%s", run_id)

                return {
                    "repo": f"{GITHUB_ORG}/{repo_name}",
                    "run_id": run_id,
                    "status": "building",
                    "download_url": None,
                }

        except Exception as exc:
            logger.error("ElectronCompiler error: %s", exc)
            return {
                "repo": f"{GITHUB_ORG}/{repo_name}",
                "run_id": None,
                "status": "failed",
                "error": str(exc),
                "download_url": None,
            }

    async def get_build_status(self, repo_name: str, run_id: str) -> dict[str, Any]:
        """
        Poll le statut d'un build GitHub Actions.
        Retourne { status, download_url }
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{GITHUB_API}/repos/{GITHUB_ORG}/{repo_name}/actions/runs/{run_id}",
                    headers=self.headers,
                )
                resp.raise_for_status()
                data = resp.json()
                conclusion = data.get("conclusion")
                status = data.get("status")

                if conclusion == "success":
                    download_url = await self._get_release_url(client, repo_name)
                    return {"status": "success", "download_url": download_url}

                if conclusion in ("failure", "cancelled"):
                    return {"status": "failed", "download_url": None}

                if status in ("queued", "in_progress", "waiting"):
                    return {"status": "building", "download_url": None}

                return {"status": "building", "download_url": None}

        except Exception as exc:
            logger.error("ElectronCompiler status error: %s", exc)
            return {"status": "failed", "download_url": None}

    def _repo_name(self, client_name: str, app_name: str) -> str:
        """Génère un nom de repo unique et propre."""
        safe_client = re.sub(r"[^a-z0-9]", "-", client_name.lower())[:20]
        safe_app = re.sub(r"[^a-z0-9]", "-", app_name.lower())[:20]
        return f"client-{safe_client}-{safe_app}".strip("-")

    async def _create_repo_from_template(
        self, client: httpx.AsyncClient, repo_name: str
    ) -> dict[str, Any]:
        """Crée un repo GitHub depuis le template."""
        resp = await client.post(
            f"{GITHUB_API}/repos/{GITHUB_ORG}/{TEMPLATE_REPO}/generate",
            headers=self.headers,
            json={
                "owner": GITHUB_ORG,
                "name": repo_name,
                "description": "CyberForge — logiciel client généré",
                "private": True,
                "include_all_branches": False,
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def _push_files(
        self,
        client: httpx.AsyncClient,
        repo_name: str,
        files: dict[str, str],
        model: str,
        license_key: str,
        version: str,
    ) -> None:
        """Pousse chaque fichier généré dans le repo."""
        for filename, content in files.items():
            if not content:
                continue

            if filename == "main.js" and model == "subscription":
                content = self._inject_license_check(content, license_key)

            content_b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
            sha = await self._get_file_sha(client, repo_name, filename)

            payload: dict[str, Any] = {
                "message": f"feat: generate {filename} — CyberForge v{version}",
                "content": content_b64,
            }
            if sha:
                payload["sha"] = sha

            resp = await client.put(
                f"{GITHUB_API}/repos/{GITHUB_ORG}/{repo_name}/contents/{filename}",
                headers=self.headers,
                json=payload,
            )
            if resp.status_code not in (200, 201):
                logger.warning(
                    "Push %s → %s: %s",
                    filename,
                    resp.status_code,
                    resp.text[:200],
                )

    async def _get_file_sha(
        self, client: httpx.AsyncClient, repo_name: str, filename: str
    ) -> str | None:
        """Récupère le SHA d'un fichier existant (nécessaire pour update)."""
        try:
            resp = await client.get(
                f"{GITHUB_API}/repos/{GITHUB_ORG}/{repo_name}/contents/{filename}",
                headers=self.headers,
            )
            if resp.status_code == 200:
                sha = resp.json().get("sha")
                return str(sha) if sha else None
        except Exception:
            pass
        return None

    async def _trigger_build(
        self, client: httpx.AsyncClient, repo_name: str, version: str
    ) -> str | None:
        """Déclenche le workflow GitHub Actions et retourne le run_id."""
        resp = await client.post(
            f"{GITHUB_API}/repos/{GITHUB_ORG}/{repo_name}/actions/workflows/build.yml/dispatches",
            headers=self.headers,
            json={"ref": "main", "inputs": {"version": version}},
        )

        if resp.status_code not in (200, 204):
            logger.warning("Trigger build → %s", resp.status_code)
            return None

        await asyncio.sleep(3)

        runs_resp = await client.get(
            f"{GITHUB_API}/repos/{GITHUB_ORG}/{repo_name}/actions/runs",
            headers=self.headers,
            params={"per_page": 1},
        )
        runs_resp.raise_for_status()
        runs = runs_resp.json().get("workflow_runs", [])
        return str(runs[0]["id"]) if runs else None

    async def _get_release_url(
        self, client: httpx.AsyncClient, repo_name: str
    ) -> str | None:
        """Récupère l'URL de téléchargement du .exe depuis les Releases GitHub."""
        try:
            resp = await client.get(
                f"{GITHUB_API}/repos/{GITHUB_ORG}/{repo_name}/releases/latest",
                headers=self.headers,
            )
            resp.raise_for_status()
            assets = resp.json().get("assets", [])
            for asset in assets:
                if str(asset.get("name", "")).endswith(".exe"):
                    return str(asset.get("browser_download_url") or "") or None
        except Exception as exc:
            logger.error("Get release URL error: %s", exc)
        return None

    def _inject_license_check(self, main_js: str, license_key: str) -> str:
        """
        Injecte la vérification de licence Stripe dans main.js.
        Au démarrage : appel API CyberForge → vérifie abonnement actif.
        """
        license_check = f"""
// ─── LICENCE CYBERFORGE ────────────────────────────────────────────────────
const {{ net }} = require('electron');

async function checkLicense() {{
  return new Promise((resolve) => {{
    const request = net.request({{
      method: 'POST',
      url: '{get_settings().backend_public_url.rstrip("/")}/api/electron/licenses/check',
    }});
    request.on('response', (response) => {{
      let data = '';
      response.on('data', (chunk) => {{ data += chunk; }});
      response.on('end', () => {{
        try {{
          const result = JSON.parse(data);
          resolve(result.active === true);
        }} catch {{ resolve(false); }}
      }});
    }});
    request.on('error', () => resolve(false));
    request.write(JSON.stringify({{ license_key: '{license_key}' }}));
    request.end();
  }});
}}
// ───────────────────────────────────────────────────────────────────────────
"""
        lines = main_js.split("\n")
        lines.insert(1, license_check)
        return "\n".join(lines)


electron_compiler = ElectronCompiler()

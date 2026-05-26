"""
Export GitHub — push du code source (gist ou dépôt configuré).
"""

from __future__ import annotations

import base64
import logging
from typing import Any

import httpx

from config import Settings, get_settings, plain_secret_str

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


class GitHubExportError(Exception):
    """Échec export GitHub."""


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def push_source_to_github(
    *,
    project_slug: str,
    files: dict[str, str],
    settings: Settings | None = None,
) -> str | None:
    """
    Pousse les fichiers vers GitHub (dépôt GITHUB_REPO ou gist de repli).
    Retourne l'URL du gist ou du dépôt, ou None si non configuré.
    """
    resolved = settings or get_settings()
    token = plain_secret_str(resolved.github_token)
    if not token:
        return None

    repo = (resolved.github_repo or "").strip()
    if repo and "/" in repo:
        try:
            return await _push_to_repo(repo, project_slug, files, token)
        except GitHubExportError as exc:
            logger.warning("Push repo GitHub échoué (%s), repli gist", exc)

    return await _create_gist(project_slug, files, token)


async def _create_gist(slug: str, files: dict[str, str], token: str) -> str:
    if not files:
        raise GitHubExportError("Aucun fichier à publier.")
    gist_files: dict[str, Any] = {}
    for path, content in files.items():
        gist_files[path] = {"content": content[:800_000]}
    body = {
        "description": f"CyberForge export — {slug}",
        "public": False,
        "files": gist_files,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{GITHUB_API}/gists",
            json=body,
            headers=_headers(token),
        )
    if resp.status_code >= 400:
        raise GitHubExportError(f"Gist HTTP {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    url = data.get("html_url")
    if not isinstance(url, str):
        raise GitHubExportError("Réponse gist sans URL.")
    return url


async def _push_to_repo(
    repo: str,
    slug: str,
    files: dict[str, str],
    token: str,
) -> str:
    owner, name = repo.split("/", 1)
    branch = f"cyberforge/{slug}"[:120]
    async with httpx.AsyncClient(timeout=60.0) as client:
        ref_resp = await client.get(
            f"{GITHUB_API}/repos/{owner}/{name}/git/ref/heads/main",
            headers=_headers(token),
        )
        if ref_resp.status_code == 404:
            ref_resp = await client.get(
                f"{GITHUB_API}/repos/{owner}/{name}/git/ref/heads/master",
                headers=_headers(token),
            )
        if ref_resp.status_code >= 400:
            raise GitHubExportError(
                f"Impossible de lire la branche par défaut ({ref_resp.status_code})."
            )
        base_sha = ref_resp.json()["object"]["sha"]

        create_ref = await client.post(
            f"{GITHUB_API}/repos/{owner}/{name}/git/refs",
            json={"ref": f"refs/heads/{branch}", "sha": base_sha},
            headers=_headers(token),
        )
        if create_ref.status_code not in (201, 422):
            raise GitHubExportError(f"Création branche HTTP {create_ref.status_code}")

        for path, content in files.items():
            put = await client.put(
                f"{GITHUB_API}/repos/{owner}/{name}/contents/{path}",
                json={
                    "message": f"ExportAI — {slug}",
                    "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
                    "branch": branch,
                },
                headers=_headers(token),
            )
            if put.status_code >= 400:
                raise GitHubExportError(f"PUT {path} HTTP {put.status_code}")

    return f"https://github.com/{owner}/{name}/tree/{branch}"

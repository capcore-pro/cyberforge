"""
Export GitHub — push du code source (gist, cyberforge repo, ou vitrines dédiées).
"""

from __future__ import annotations

import base64
import logging
import re
from typing import Any

import httpx

from config import Settings, get_settings, plain_secret_str

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
DEFAULT_VITRINES_REPO = "mathiasgibiard-dotcom/vitrines"


class GitHubExportError(Exception):
    """Échec export GitHub."""


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def vitrine_branch_name(slug: str) -> str:
    """Nom de branche GitHub sûr (une branche = un site vitrine)."""
    branch = re.sub(r"[^a-z0-9/_-]+", "-", slug.lower().strip())
    branch = re.sub(r"-{2,}", "-", branch).strip("-")
    return (branch or "vitrine-site")[:100]


def _resolve_vitrines_repo(settings: Settings) -> str:
    explicit = (getattr(settings, "vitrines_github_repo", None) or "").strip()
    return explicit or DEFAULT_VITRINES_REPO


async def ensure_github_repo(
    repo: str,
    token: str,
    *,
    description: str = "Sites vitrines Next.js générés par CyberForge (une branche par site).",
    private: bool = True,
) -> bool:
    """
    Crée le dépôt s'il n'existe pas. Retourne True si créé, False s'il existait déjà.
    """
    owner, name = repo.split("/", 1)
    async with httpx.AsyncClient(timeout=60.0) as client:
        check = await client.get(
            f"{GITHUB_API}/repos/{owner}/{name}",
            headers=_headers(token),
        )
        if check.status_code == 200:
            return False
        if check.status_code != 404:
            raise GitHubExportError(
                f"Lecture dépôt {repo} HTTP {check.status_code}: {check.text[:200]}"
            )

        body: dict[str, Any] = {
            "name": name,
            "description": description,
            "private": private,
            "auto_init": True,
        }
        org_resp = await client.post(
            f"{GITHUB_API}/orgs/{owner}/repos",
            json=body,
            headers=_headers(token),
        )
        if org_resp.status_code == 201:
            logger.info("Dépôt GitHub créé (org) : %s", repo)
            return True

        user_body = {**body, "name": name}
        user_resp = await client.post(
            f"{GITHUB_API}/user/repos",
            json=user_body,
            headers=_headers(token),
        )
        if user_resp.status_code == 201:
            logger.info("Dépôt GitHub créé (user) : %s", repo)
            return True

        detail = org_resp.text[:300] if org_resp.status_code >= 400 else user_resp.text[:300]
        raise GitHubExportError(
            f"Création dépôt {repo} impossible "
            f"(org HTTP {org_resp.status_code}, user HTTP {user_resp.status_code}): {detail}"
        )


async def push_vitrine_site_to_github(
    *,
    branch_slug: str,
    files: dict[str, str],
    settings: Settings | None = None,
    repo: str | None = None,
) -> str:
    """
    Pousse un site vitrine complet sur une branche dédiée (contenu remplacé à chaque export).

    Chaque branche ne contient que les fichiers du site (commit unique, sans historique cyberforge).
  """
    if not files:
        raise GitHubExportError("Aucun fichier vitrine à publier.")

    resolved = settings or get_settings()
    token = plain_secret_str(resolved.github_token)
    if not token:
        raise GitHubExportError("GITHUB_TOKEN non configuré.")

    target_repo = (repo or _resolve_vitrines_repo(resolved)).strip()
    if "/" not in target_repo:
        raise GitHubExportError(f"Dépôt vitrines invalide : {target_repo!r}")

    await ensure_github_repo(target_repo, token)

    owner, name = target_repo.split("/", 1)
    branch = vitrine_branch_name(branch_slug)

    async with httpx.AsyncClient(timeout=120.0) as client:
        tree_items: list[dict[str, str]] = []
        for path in sorted(files.keys()):
            content = files[path]
            if not path or content is None:
                continue
            blob_resp = await client.post(
                f"{GITHUB_API}/repos/{owner}/{name}/git/blobs",
                json={"content": content, "encoding": "utf-8"},
                headers=_headers(token),
            )
            if blob_resp.status_code >= 400:
                raise GitHubExportError(
                    f"Blob {path} HTTP {blob_resp.status_code}: {blob_resp.text[:200]}"
                )
            tree_items.append(
                {
                    "path": path.lstrip("/"),
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob_resp.json()["sha"],
                }
            )

        if not tree_items:
            raise GitHubExportError("Aucun blob Git créé.")

        tree_resp = await client.post(
            f"{GITHUB_API}/repos/{owner}/{name}/git/trees",
            json={"tree": tree_items},
            headers=_headers(token),
        )
        if tree_resp.status_code >= 400:
            raise GitHubExportError(
                f"Tree HTTP {tree_resp.status_code}: {tree_resp.text[:200]}"
            )
        tree_sha = tree_resp.json()["sha"]

        ref_path = f"heads/{branch}"
        ref_resp = await client.get(
            f"{GITHUB_API}/repos/{owner}/{name}/git/ref/{ref_path}",
            headers=_headers(token),
        )
        parents: list[str] = []
        if ref_resp.status_code == 200:
            parents = [ref_resp.json()["object"]["sha"]]

        commit_resp = await client.post(
            f"{GITHUB_API}/repos/{owner}/{name}/git/commits",
            json={
                "message": f"CyberForge vitrine — {branch}",
                "tree": tree_sha,
                "parents": parents,
            },
            headers=_headers(token),
        )
        if commit_resp.status_code >= 400:
            raise GitHubExportError(
                f"Commit HTTP {commit_resp.status_code}: {commit_resp.text[:200]}"
            )
        commit_sha = commit_resp.json()["sha"]

        if ref_resp.status_code == 200:
            update = await client.patch(
                f"{GITHUB_API}/repos/{owner}/{name}/git/refs/{ref_path}",
                json={"sha": commit_sha, "force": True},
                headers=_headers(token),
            )
            if update.status_code >= 400:
                raise GitHubExportError(
                    f"Mise à jour branche HTTP {update.status_code}: {update.text[:200]}"
                )
        else:
            create = await client.post(
                f"{GITHUB_API}/repos/{owner}/{name}/git/refs",
                json={"ref": f"refs/heads/{branch}", "sha": commit_sha},
                headers=_headers(token),
            )
            if create.status_code >= 400:
                raise GitHubExportError(
                    f"Création branche HTTP {create.status_code}: {create.text[:200]}"
                )

    url = f"https://github.com/{owner}/{name}/tree/{branch}"
    logger.info("Vitrine publiée | repo=%s | branch=%s | files=%s", target_repo, branch, len(files))
    return url


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

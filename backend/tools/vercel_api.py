"""
Client minimal Vercel (REST) — utilisé pour automatiser les déploiements.

Objectif V1 :
- retrouver/poller le dernier deployment lié à une branche GitHub (meta.githubCommitRef)
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx

from config import Settings, get_settings, plain_secret_str

VERCEL_API = "https://api.vercel.com"


class VercelError(Exception):
    pass


@dataclass(frozen=True)
class VercelDeployment:
    id: str
    url: str | None
    ready_state: str | None
    state: str | None
    meta: dict[str, Any]
    git_ref: str | None = None


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _token(settings: Settings | None = None) -> str:
    resolved = settings or get_settings()
    token = plain_secret_str(getattr(resolved, "vercel_token", None))
    if not token:
        raise VercelError("VERCEL_TOKEN manquant.")
    return token


def _team_id(settings: Settings | None = None) -> str | None:
    resolved = settings or get_settings()
    raw = (getattr(resolved, "vercel_team_id", None) or "").strip()
    return raw or None


def _project_id(settings: Settings | None = None) -> str | None:
    resolved = settings or get_settings()
    raw = (getattr(resolved, "vercel_vitrines_project_id", None) or "").strip()
    return raw or None


def _project_name(settings: Settings | None = None) -> str:
    resolved = settings or get_settings()
    raw = (getattr(resolved, "vercel_vitrines_project_name", None) or "").strip()
    return raw or "vitrines"


async def resolve_vitrines_project_id(settings: Settings | None = None) -> str:
    """
    Résout l'ID du projet Vercel 'vitrines' (teamId optionnel).
    """
    explicit = _project_id(settings)
    if explicit:
        return explicit

    token = _token(settings)
    name = _project_name(settings)
    team_id = _team_id(settings)
    params = {"teamId": team_id} if team_id else None
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(
            f"{VERCEL_API}/v9/projects/{name}",
            headers=_headers(token),
            params=params,
        )
        if r.status_code >= 400:
            raise VercelError(f"Vercel get project {name} HTTP {r.status_code}: {r.text[:300]}")
        data = r.json()
        pid = data.get("id") or data.get("projectId")
        if not pid:
            raise VercelError("Vercel project id introuvable dans la réponse.")
        return str(pid)


async def ensure_project_for_vitrine_branch(
    *,
    project_name: str,
    github_repo: str,
    production_branch: str,
    vitrine_backend_url: str,
    settings: Settings | None = None,
) -> str:
    """
    Crée (si besoin) un projet Vercel par vitrine pour obtenir une URL propre:
    https://<project_name>.vercel.app
    """
    token = _token(settings)
    team_id = _team_id(settings)
    params = {"teamId": team_id} if team_id else None

    async with httpx.AsyncClient(timeout=60.0) as client:
        # already exists?
        get_resp = await client.get(
            f"{VERCEL_API}/v9/projects/{project_name}",
            headers=_headers(token),
            params=params,
        )
        if get_resp.status_code == 200:
            data = get_resp.json()
            pid = data.get("id")
            if pid:
                # Ensure production branch is correct (undocumented endpoint used by dashboard)
                try:
                    current = (data.get("link") or {}).get("productionBranch")
                except Exception:
                    current = None
                if current != production_branch:
                    await _set_production_branch(project_name, production_branch, token, team_id)
                return str(pid)
        elif get_resp.status_code not in (404,):
            raise VercelError(
                f"Vercel get project {project_name} HTTP {get_resp.status_code}: {get_resp.text[:300]}"
            )

        body: dict[str, Any] = {
            "name": project_name,
            "framework": "nextjs",
            "gitRepository": {"type": "github", "repo": github_repo, "productionBranch": production_branch},
            "environmentVariables": [
                {
                    "key": "VITRINE_BACKEND_URL",
                    "value": vitrine_backend_url,
                    "target": ["production", "preview", "development"],
                    "type": "plain",
                }
            ],
        }
        create = await client.post(
            f"{VERCEL_API}/v11/projects",
            headers=_headers(token),
            params=params,
            json=body,
        )
        if create.status_code in (200, 201):
            pid = create.json().get("id")
            if not pid:
                raise VercelError("Création projet Vercel sans id.")
            await _set_production_branch(project_name, production_branch, token, team_id)
            return str(pid)
        # If race/exists, re-fetch
        if create.status_code in (409,):
            again = await client.get(
                f"{VERCEL_API}/v9/projects/{project_name}",
                headers=_headers(token),
                params=params,
            )
            if again.status_code == 200 and again.json().get("id"):
                return str(again.json()["id"])
        raise VercelError(f"Vercel create project HTTP {create.status_code}: {create.text[:500]}")


async def _set_production_branch(
    project_name: str,
    branch: str,
    token: str,
    team_id: str | None,
) -> None:
    """
    Endpoint non documenté (utilisé par le dashboard) pour changer la production branch.
    """
    params = {"teamId": team_id} if team_id else None
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.patch(
            f"https://vercel.com/api/v9/projects/{project_name}/branch",
            headers=_headers(token),
            params=params,
            json={"branch": branch},
        )
        if r.status_code >= 400:
            raise VercelError(
                f"Vercel set production branch HTTP {r.status_code}: {r.text[:300]}"
            )


async def delete_project(
    id_or_name: str,
    *,
    settings: Settings | None = None,
) -> bool:
    token = _token(settings)
    team_id = _team_id(settings)
    params = {"teamId": team_id} if team_id else None
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.delete(
            f"{VERCEL_API}/v9/projects/{id_or_name}",
            headers=_headers(token),
            params=params,
        )
        if r.status_code in (204, 200):
            return True
        if r.status_code == 404:
            return False
        raise VercelError(f"Vercel delete project HTTP {r.status_code}: {r.text[:300]}")


async def list_deployments_for_branch(
    *,
    branch: str,
    project_id: str,
    settings: Settings | None = None,
    limit: int = 10,
) -> list[VercelDeployment]:
    token = _token(settings)
    team_id = _team_id(settings)
    params: dict[str, str] = {"projectId": project_id, "limit": str(limit)}
    if team_id:
        params["teamId"] = team_id

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(
            f"{VERCEL_API}/v6/deployments",
            headers=_headers(token),
            params=params,
        )
        if r.status_code >= 400:
            raise VercelError(f"Vercel list deployments HTTP {r.status_code}: {r.text[:400]}")
        deployments = r.json().get("deployments", [])
        result: list[VercelDeployment] = []
        for d in deployments:
            meta = d.get("meta") if isinstance(d.get("meta"), dict) else {}
            ref = (
                meta.get("githubCommitRef")
                or meta.get("gitCommitRef")
                or (d.get("gitSource") or {}).get("ref")
            )
            if ref != branch:
                continue
            result.append(
                VercelDeployment(
                    id=str(d.get("uid") or d.get("id")),
                    url=d.get("url"),
                    ready_state=d.get("readyState"),
                    state=d.get("state"),
                    meta=meta,
                    git_ref=ref,
                )
            )
        return result


async def trigger_git_deploy(
    *,
    project_name: str,
    github_org: str,
    github_repo: str,
    git_ref: str,
    target: str = "production",
    settings: Settings | None = None,
) -> VercelDeployment:
    """
    Déclenche un déploiement Git explicite (évite d'attendre un webhook).
    POST /v13/deployments
    """
    token = _token(settings)
    team_id = _team_id(settings)
    params = {"teamId": team_id} if team_id else None
    body = {
        "name": project_name,
        "project": project_name,
        "target": target,
        "gitSource": {
            "type": "github",
            "org": github_org,
            "repo": github_repo,
            "ref": git_ref,
        },
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            f"{VERCEL_API}/v13/deployments",
            headers=_headers(token),
            params=params,
            json=body,
        )
        if r.status_code >= 400:
            raise VercelError(f"Vercel trigger deploy HTTP {r.status_code}: {r.text[:400]}")
        data = r.json()
        did = data.get("id") or data.get("uid")
        return VercelDeployment(
            id=str(did),
            url=data.get("url"),
            ready_state=data.get("readyState"),
            state=data.get("state"),
            meta=data.get("meta") if isinstance(data.get("meta"), dict) else {},
            git_ref=git_ref,
        )


async def get_deployment(
    deployment_id: str,
    *,
    settings: Settings | None = None,
) -> VercelDeployment:
    token = _token(settings)
    team_id = _team_id(settings)
    params = {"teamId": team_id} if team_id else None
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(
            f"{VERCEL_API}/v6/deployments/{deployment_id}",
            headers=_headers(token),
            params=params,
        )
        if r.status_code >= 400:
            raise VercelError(f"Vercel get deployment HTTP {r.status_code}: {r.text[:400]}")
        d = r.json()
        meta = d.get("meta") if isinstance(d.get("meta"), dict) else {}
        ref = (d.get("gitSource") or {}).get("ref") or meta.get("githubCommitRef")
        return VercelDeployment(
            id=str(d.get("id") or deployment_id),
            url=d.get("url"),
            ready_state=d.get("readyState"),
            state=d.get("state"),
            meta=meta,
            git_ref=ref,
        )


async def wait_for_deployment_ready(
    deployment_id: str,
    *,
    settings: Settings | None = None,
    timeout_seconds: float = 240.0,
    poll_seconds: float = 3.0,
) -> VercelDeployment:
    start = time.time()
    while time.time() - start < timeout_seconds:
        dep = await get_deployment(deployment_id, settings=settings)
        if dep.ready_state in {"READY", "ERROR", "CANCELED"}:
            return dep
        await _async_sleep(poll_seconds)
    return await get_deployment(deployment_id, settings=settings)


async def delete_deployment(
    deployment_id: str,
    *,
    settings: Settings | None = None,
) -> bool:
    """
    DELETE /v13/deployments/{id}
    Retourne True si supprimé, False si introuvable.
    """
    token = _token(settings)
    team_id = _team_id(settings)
    params = {"teamId": team_id} if team_id else None
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.delete(
            f"{VERCEL_API}/v13/deployments/{deployment_id}",
            headers=_headers(token),
            params=params,
        )
        if r.status_code in (200, 204):
            return True
        if r.status_code == 404:
            return False
        raise VercelError(f"Vercel delete deployment HTTP {r.status_code}: {r.text[:300]}")


async def delete_deployments_for_branch(
    *,
    branch: str,
    project_id: str,
    settings: Settings | None = None,
    limit: int = 20,
) -> dict[str, int]:
    """
    Supprime les derniers déploiements Vercel associés à une branche.
    """
    deployments = await list_deployments_for_branch(
        branch=branch,
        project_id=project_id,
        settings=settings,
        limit=limit,
    )
    deleted = 0
    missing = 0
    for d in deployments:
        ok = await delete_deployment(d.id, settings=settings)
        if ok:
            deleted += 1
        else:
            missing += 1
    return {"deleted": deleted, "missing": missing, "considered": len(deployments)}


async def wait_for_branch_deployment_ready(
    *,
    branch: str,
    project_id: str,
    settings: Settings | None = None,
    timeout_seconds: float = 240.0,
    poll_seconds: float = 4.0,
) -> VercelDeployment:
    """
    Attend qu'un déploiement lié à branch (dans meta) soit READY/ERROR.
    """
    start = time.time()
    last_seen: VercelDeployment | None = None
    while time.time() - start < timeout_seconds:
        deployments = await list_deployments_for_branch(
            branch=branch,
            project_id=project_id,
            settings=settings,
            limit=10,
        )
        if deployments:
            last_seen = deployments[0]
            dep = await get_deployment(last_seen.id, settings=settings)
            if dep.ready_state in {"READY", "ERROR", "CANCELED"}:
                return dep
        await _async_sleep(poll_seconds)
    if last_seen:
        return await get_deployment(last_seen.id, settings=settings)
    raise VercelError(f"Aucun deployment Vercel trouvé pour la branche {branch!r}.")


async def _async_sleep(seconds: float) -> None:
    import asyncio

    await asyncio.sleep(seconds)


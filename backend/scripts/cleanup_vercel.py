"""
Nettoyage Vercel — supprime tous les déploiements de tous les projets.

IMPORTANT: ne supprime PAS les projets, uniquement leurs déploiements.

Variable d'env requise:
  - VERCEL_TOKEN

API:
  - List projects:      GET    https://api.vercel.com/v9/projects
  - List deployments:   GET    https://api.vercel.com/v6/deployments?projectId={projectId}
  - Delete deployment:  DELETE https://api.vercel.com/v13/deployments/{deploymentId}

Pagination:
  - Projets: champ "pagination.next" (si présent)
  - Déploiements: champ "pagination.next" ou paramètre "until" (fallback)
"""

from __future__ import annotations

import os
from typing import Any, Iterable

import requests


API_BASE = "https://api.vercel.com"


def _require_env(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if not value:
        raise RuntimeError(f"Variable d'env manquante: {name}")
    return value


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _chunked(seq: list[Any], size: int) -> Iterable[list[Any]]:
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def _get_json(resp: requests.Response) -> dict[str, Any]:
    resp.raise_for_status()
    payload = resp.json()
    if isinstance(payload, dict) and payload.get("error"):
        raise RuntimeError(str(payload["error"]))
    return payload if isinstance(payload, dict) else {"result": payload}


def _iter_projects(session: requests.Session) -> Iterable[dict[str, Any]]:
    next_cursor: str | None = None
    while True:
        url = f"{API_BASE}/v9/projects"
        params = {}
        if next_cursor:
            params["next"] = next_cursor
        payload = _get_json(session.get(url, params=params, timeout=30))
        projects = payload.get("projects") or payload.get("result") or []
        if not isinstance(projects, list) or not projects:
            return
        for p in projects:
            if isinstance(p, dict):
                yield p

        pagination = payload.get("pagination") or {}
        next_cursor = pagination.get("next")
        if not next_cursor:
            return


def _list_deployments_for_project(
    session: requests.Session, project_id: str
) -> list[dict[str, Any]]:
    deployments: list[dict[str, Any]] = []
    next_cursor: str | None = None
    until: int | None = None

    while True:
        url = f"{API_BASE}/v6/deployments"
        params: dict[str, Any] = {"projectId": project_id, "limit": 100}
        if next_cursor:
            params["next"] = next_cursor
        if until is not None:
            params["until"] = until

        payload = _get_json(session.get(url, params=params, timeout=30))
        batch = payload.get("deployments") or payload.get("result") or []
        if not isinstance(batch, list) or not batch:
            break
        for d in batch:
            if isinstance(d, dict):
                deployments.append(d)

        pagination = payload.get("pagination") or {}
        next_cursor = pagination.get("next")
        if next_cursor:
            continue

        # fallback: si "next" absent, Vercel supporte souvent "until"
        # on récupère le plus ancien "createdAt" du batch pour paginer
        created_ats = [
            int(d.get("createdAt"))
            for d in batch
            if isinstance(d.get("createdAt"), (int, float))
        ]
        if created_ats and len(batch) >= 100:
            until = min(created_ats) - 1
            continue

        break

    return deployments


def _delete_deployment(session: requests.Session, deployment_id: str) -> None:
    url = f"{API_BASE}/v13/deployments/{deployment_id}"
    payload = _get_json(session.delete(url, timeout=30))
    # Certaines réponses n'ont pas "success"; l'absence d'erreur + 2xx suffit.
    _ = payload


def main() -> int:
    token = _require_env("VERCEL_TOKEN")

    total_deleted = 0
    with requests.Session() as session:
        session.headers.update(_headers(token))

        for project in _iter_projects(session):
            project_id = str(project.get("id") or "").strip()
            name = str(project.get("name") or "").strip()
            if not project_id or not name:
                continue

            print(f"\n{name} {project_id}".strip())

            deployments = _list_deployments_for_project(session, project_id)
            deleted_for_project = 0

            for dep in deployments:
                dep_id = str(dep.get("uid") or dep.get("id") or "").strip()
                if not dep_id:
                    continue
                _delete_deployment(session, dep_id)
                deleted_for_project += 1

            total_deleted += deleted_for_project
            print(f"{name}: {deleted_for_project} déploiement(s) supprimé(s)")

    print(f"\nTotal global supprimé: {total_deleted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


"""
Nettoyage Cloudflare Pages — supprime tous les déploiements d'un projet.

Projet ciblé: cyberforge-demos
IMPORTANT: ne supprime PAS le projet, uniquement ses déploiements.

Variables d'env requises:
  - CLOUDFLARE_ACCOUNT_ID
  - CLOUDFLARE_API_TOKEN

Exécution:
  python backend/scripts/cleanup_cloudflare.py
"""

from __future__ import annotations

import os

import requests


PROJECT_NAME = "cyberforge-demos"
API_BASE = "https://api.cloudflare.com/client/v4"


def _require_env(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if not value:
        raise RuntimeError(f"Variable d'env manquante: {name}")
    return value


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _project_exists(session: requests.Session, account_id: str) -> bool:
    url = f"{API_BASE}/accounts/{account_id}/pages/projects/{PROJECT_NAME}"
    resp = session.get(url, timeout=30)
    if resp.status_code in (400, 404):
        print(f"Projet {PROJECT_NAME} introuvable ou account_id incorrect")
        return False
    resp.raise_for_status()
    payload = resp.json()
    if not isinstance(payload, dict) or not payload.get("success", False):
        print(f"Projet {PROJECT_NAME} introuvable ou account_id incorrect")
        return False
    return True


def _get_deployments(session: requests.Session, account_id: str) -> list[dict]:
    url = f"{API_BASE}/accounts/{account_id}/pages/projects/{PROJECT_NAME}/deployments"
    resp = session.get(url, timeout=30)
    if resp.status_code == 400:
        print("Aucun déploiement à supprimer sur Cloudflare")
        return []
    resp.raise_for_status()
    payload = resp.json()

    if not payload.get("success", False):
        errors = payload.get("errors") or payload.get("messages") or payload
        raise RuntimeError(f"Cloudflare API error (list deployments): {errors}")

    batch = payload.get("result")
    if not isinstance(batch, list):
        return []

    return [d for d in batch if isinstance(d, dict)]


def _is_live_production_deployment(dep: dict) -> bool:
    env = dep.get("environment")
    if isinstance(env, dict):
        env_name = env.get("name") or env.get("type") or ""
    else:
        env_name = env or ""

    status = dep.get("status") or dep.get("deployment_status") or ""
    status_str = str(status).strip().lower()
    env_str = str(env_name).strip().lower()
    return env_str == "production" and status_str == "active"


def _delete_deployment(
    session: requests.Session, account_id: str, deployment_id: str
) -> None:
    url = (
        f"{API_BASE}/accounts/{account_id}/pages/projects/{PROJECT_NAME}"
        f"/deployments/{deployment_id}"
    )
    resp = session.delete(url, params={"force": "true"}, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    if not payload.get("success", False):
        errors = payload.get("errors") or payload.get("messages") or payload
        raise RuntimeError(
            f"Cloudflare API error (delete deployment {deployment_id}): {errors}"
        )


def main() -> int:
    account_id = _require_env("CLOUDFLARE_ACCOUNT_ID")
    token = _require_env("CLOUDFLARE_API_TOKEN")

    deleted = 0
    with requests.Session() as session:
        session.headers.update(_headers(token))

        if not _project_exists(session, account_id):
            return 0

        deployments = _get_deployments(session, account_id)
        for dep in deployments:
            deployment_id = str(dep.get("id") or "").strip()
            dep_url = (
                dep.get("url")
                or dep.get("deployment_url")
                or dep.get("environment_url")
                or ""
            )
            if not deployment_id:
                continue

            if _is_live_production_deployment(dep):
                print(f"{deployment_id} {str(dep_url).strip()} (conservé: production/active)".strip())
                continue

            print(f"{deployment_id} {str(dep_url).strip()}".strip())
            _delete_deployment(session, account_id, deployment_id)
            deleted += 1

    print(f"Déploiements supprimés: {deleted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


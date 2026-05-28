"""
Export Railway — création de projet pour apps backend / full-stack.
"""

from __future__ import annotations

import logging
import re

import httpx

from config import Settings, get_settings, plain_secret_str

logger = logging.getLogger(__name__)

RAILWAY_GRAPHQL = "https://backboard.railway.com/graphql/v2"


class RailwayExportError(Exception):
    """Échec export Railway."""


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


async def _gql(
    query: str,
    variables: dict,
    *,
    token: str,
    timeout: float = 60.0,
) -> dict:
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            RAILWAY_GRAPHQL,
            json={"query": query, "variables": variables},
            headers=_headers(token),
        )
    if resp.status_code >= 400:
        raise RailwayExportError(f"Railway HTTP {resp.status_code}: {resp.text[:300]}")
    payload = resp.json()
    if payload.get("errors"):
        errors = payload["errors"]
        msg = (
            errors[0].get("message", str(errors))
            if isinstance(errors, list) and errors
            else str(errors)
        )
        raise RailwayExportError(msg)
    return payload.get("data") or {}


async def _get_default_environment_id(*, project_id: str, token: str) -> str:
    data = await _gql(
        """
        query($id: String!) {
          project(id: $id) {
            environments { id name }
          }
        }
        """.strip(),
        {"id": project_id},
        token=token,
    )
    envs = ((data.get("project") or {}).get("environments") or []) if isinstance(data, dict) else []
    if not envs:
        raise RailwayExportError("Projet Railway sans environment.")
    # prefer "production" if present
    for e in envs:
        if (e.get("name") or "").lower() == "production" and e.get("id"):
            return str(e["id"])
    return str(envs[0]["id"])


async def _service_create(*, project_id: str, name: str, token: str) -> str:
    data = await _gql(
        """
        mutation($input: ServiceCreateInput!) {
          serviceCreate(input: $input) { id name }
        }
        """.strip(),
        {"input": {"projectId": project_id, "name": name}},
        token=token,
    )
    svc = (data.get("serviceCreate") or {}) if isinstance(data, dict) else {}
    sid = svc.get("id")
    if not sid:
        raise RailwayExportError("serviceCreate sans id.")
    return str(sid)


async def _environment_stage_changes(
    *,
    environment_id: str,
    payload: dict,
    token: str,
    merge: bool = True,
) -> None:
    await _gql(
        """
        mutation($environmentId: String!, $payload: EnvironmentConfig!, $merge: Boolean) {
          environmentStageChanges(environmentId: $environmentId, input: $payload, merge: $merge)
        }
        """.strip(),
        {"environmentId": environment_id, "payload": payload, "merge": merge},
        token=token,
    )


async def _environment_commit_staged(
    *,
    environment_id: str,
    message: str,
    token: str,
    skip_deploys: bool = False,
) -> None:
    await _gql(
        """
        mutation($environmentId: String!, $message: String, $skipDeploys: Boolean) {
          environmentPatchCommitStaged(environmentId: $environmentId, commitMessage: $message, skipDeploys: $skipDeploys) {
            id
          }
        }
        """.strip(),
        {"environmentId": environment_id, "message": message, "skipDeploys": skip_deploys},
        token=token,
    )


async def _service_domain_create(*, environment_id: str, service_id: str, token: str) -> None:
    await _gql(
        """
        mutation ($environmentId: String!, $serviceId: String!) {
          serviceDomainCreate(input: {environmentId: $environmentId, serviceId: $serviceId}) {
            createdAt
          }
        }
        """.strip(),
        {"environmentId": environment_id, "serviceId": service_id},
        token=token,
    )


async def _get_service_domains(
    *,
    environment_id: str,
    service_id: str,
    token: str,
) -> list[str]:
    data = await _gql(
        """
        query($environmentId: String!, $serviceId: String!) {
          serviceDomains(environmentId: $environmentId, serviceId: $serviceId) {
            domain
          }
        }
        """.strip(),
        {"environmentId": environment_id, "serviceId": service_id},
        token=token,
    )
    rows = (data.get("serviceDomains") or []) if isinstance(data, dict) else []
    domains: list[str] = []
    for row in rows:
        d = (row.get("domain") or "").strip()
        if d:
            domains.append(d)
    return domains


async def deploy_to_railway(
    *,
    project_name: str,
    settings: Settings | None = None,
) -> tuple[str, str]:
    """
    Crée un projet Railway et retourne (production_url, project_id).
  """
    resolved = settings or get_settings()
    token = plain_secret_str(resolved.railway_api_key)
    if not token:
        raise RailwayExportError("RAILWAY_API_KEY non configurée.")

    safe_name = re.sub(r"[^\w\s-]", "", project_name)[:60].strip() or "CyberForge App"
    query = """
    mutation projectCreate($name: String!) {
      projectCreate(input: { name: $name }) {
        id
        name
      }
    }
    """
    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post(
            RAILWAY_GRAPHQL,
            json={"query": query, "variables": {"name": safe_name}},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )

    if resp.status_code >= 400:
        raise RailwayExportError(f"Railway HTTP {resp.status_code}: {resp.text[:300]}")

    payload = resp.json()
    errors = payload.get("errors")
    if errors:
        msg = errors[0].get("message", str(errors)) if isinstance(errors, list) else str(errors)
        raise RailwayExportError(msg)

    data = (payload.get("data") or {}).get("projectCreate") or {}
    project_id = data.get("id")
    if not project_id:
        raise RailwayExportError("Railway n'a pas renvoyé d'identifiant projet.")

    production_url = f"https://railway.app/project/{project_id}"
    return production_url, str(project_id)


async def deploy_github_backend_service(
    *,
    project_name: str,
    github_repo: str,
    branch: str,
    root_directory: str = "backend",
    start_command: str | None = None,
    settings: Settings | None = None,
) -> tuple[str, str, str]:
    """
    Creates a Railway project + service, links it to a GitHub repo branch,
    provisions a public domain, and returns:
      (backend_url, railway_project_id, railway_service_id)
    """
    resolved = settings or get_settings()
    token = plain_secret_str(resolved.railway_api_key)
    if not token:
        raise RailwayExportError("RAILWAY_API_KEY non configurée.")
    if "/" not in github_repo:
        raise RailwayExportError(f"GitHub repo invalide: {github_repo!r}")

    safe_name = re.sub(r"[^\w\s-]", "", project_name)[:60].strip() or "CyberForge App"

    # 1) Create project
    data = await _gql(
        """
        mutation projectCreate($name: String!) {
          projectCreate(input: { name: $name }) { id name }
        }
        """.strip(),
        {"name": safe_name},
        token=token,
        timeout=45.0,
    )
    proj = (data.get("projectCreate") or {}) if isinstance(data, dict) else {}
    project_id = proj.get("id")
    if not project_id:
        raise RailwayExportError("Railway n'a pas renvoyé d'identifiant projet.")
    project_id = str(project_id)

    # 2) Resolve environment
    environment_id = await _get_default_environment_id(project_id=project_id, token=token)

    # 3) Create empty service
    service_id = await _service_create(project_id=project_id, name="backend", token=token)

    # 4) Stage config: link to repo/branch, set root dir and start command
    payload: dict = {
        "services": {
            service_id: {
                "isCreated": True,
                "source": {"repo": github_repo, "branch": branch, "rootDirectory": root_directory},
                "variables": {
                    "PORT": {"value": "8000"},
                },
            }
        }
    }
    if start_command:
        payload["services"][service_id]["deploy"] = {"startCommand": start_command}

    await _environment_stage_changes(environment_id=environment_id, payload=payload, token=token, merge=True)
    await _environment_commit_staged(
        environment_id=environment_id,
        message=f"CyberForge: link backend to {github_repo}@{branch}",
        token=token,
        skip_deploys=False,
    )

    # 5) Ensure domain
    await _service_domain_create(environment_id=environment_id, service_id=service_id, token=token)
    domains = await _get_service_domains(environment_id=environment_id, service_id=service_id, token=token)
    if not domains:
        # still return dashboard URL as fallback
        backend_url = f"https://railway.app/project/{project_id}"
        return backend_url, project_id, service_id

    backend_url = "https://" + domains[0]
    return backend_url, project_id, service_id

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
            environments {
              edges { node { id name } }
            }
          }
        }
        """.strip(),
        {"id": project_id},
        token=token,
    )
    project = (data.get("project") or {}) if isinstance(data, dict) else {}
    envs_blob = project.get("environments") or {}
    envs: list[dict] = []
    if isinstance(envs_blob, list):
        envs = [e for e in envs_blob if isinstance(e, dict)]
    elif isinstance(envs_blob, dict):
        edges = envs_blob.get("edges")
        if isinstance(edges, list):
            for edge in edges:
                if isinstance(edge, dict) and isinstance(edge.get("node"), dict):
                    envs.append(edge["node"])

    if not envs:
        raise RailwayExportError("Projet Railway sans environment.")
    # prefer "production" if present
    for e in envs:
        if (e.get("name") or "").lower() == "production" and e.get("id"):
            return str(e["id"])
    return str(envs[0]["id"])


async def _resolve_workspace_id(*, token: str, preferred: str | None = None) -> str:
    if preferred and preferred.strip():
        return preferred.strip()
    data = await _gql(
        """
        query {
          me {
            workspaces { id name }
          }
        }
        """.strip(),
        {},
        token=token,
    )
    me = (data.get("me") or {}) if isinstance(data, dict) else {}
    wss_blob = me.get("workspaces") or []
    wss: list[dict] = []
    if isinstance(wss_blob, list):
        wss = [w for w in wss_blob if isinstance(w, dict)]
    if not wss:
        raise RailwayExportError("Impossible de résoudre le workspace Railway (me.workspaces vide).")
    return str(wss[0]["id"])


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
          environmentStageChanges(environmentId: $environmentId, input: $payload, merge: $merge) {
            id
          }
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
    workspace_id = await _resolve_workspace_id(token=token, preferred=getattr(resolved, "railway_workspace_id", None))
    query = """
    mutation projectCreate($name: String!, $workspaceId: String!) {
      projectCreate(input: { name: $name, workspaceId: $workspaceId }) {
        id
        name
      }
    }
    """
    payload = await _gql(query.strip(), {"name": safe_name, "workspaceId": workspace_id}, token=token, timeout=45.0)
    data = payload.get("projectCreate") or {}
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
    shared_project_id: str | None = None,
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

    if shared_project_id and shared_project_id.strip():
        logger.info("Railway Option C | shared_project_id=%s | service_branch=%s", shared_project_id.strip(), branch)

    safe_name = re.sub(r"[^\w\s-]", "", project_name)[:60].strip() or "CyberForge App"
    # 1) Project (Option C: reuse a single shared project)
    if shared_project_id and shared_project_id.strip():
        project_id = shared_project_id.strip()
    else:
        workspace_id = await _resolve_workspace_id(
            token=token,
            preferred=getattr(resolved, "railway_workspace_id", None),
        )
        data = await _gql(
            """
            mutation projectCreate($name: String!, $workspaceId: String!) {
              projectCreate(input: { name: $name, workspaceId: $workspaceId }) { id name }
            }
            """.strip(),
            {"name": safe_name, "workspaceId": workspace_id},
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
    service_id = await _service_create(project_id=project_id, name=f"api-{branch[:24]}", token=token)

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


async def delete_railway_service(*, service_id: str, token: str) -> bool:
    data = await _gql(
        """
        mutation($id: String!) { serviceDelete(id: $id) }
        """.strip(),
        {"id": service_id},
        token=token,
    )
    return bool(data.get("serviceDelete")) if isinstance(data, dict) else False


async def delete_railway_project(*, project_id: str, token: str) -> bool:
    data = await _gql(
        """
        mutation($id: String!) { projectDelete(id: $id) }
        """.strip(),
        {"id": project_id},
        token=token,
    )
    return bool(data.get("projectDelete")) if isinstance(data, dict) else False

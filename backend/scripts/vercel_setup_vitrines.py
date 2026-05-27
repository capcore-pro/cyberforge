"""Configure le projet Vercel pour mathiasgibiard-dotcom/vitrines (API REST)."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

import config  # noqa: F401

from config import get_settings, plain_secret_str

VERCEL_API = "https://api.vercel.com"
PROJECT_NAME = "vitrines"
GITHUB_REPO = "mathiasgibiard-dotcom/vitrines"
BACKEND_URL = "https://cyberforge-backend-production.up.railway.app"


def _token() -> str:
    settings = get_settings()
    token = plain_secret_str(getattr(settings, "vercel_token", None))
    if not token:
        token = __import__("os").environ.get("VERCEL_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "VERCEL_TOKEN manquant. Créez un token sur https://vercel.com/account/tokens "
            "et ajoutez-le dans backend/.env"
        )
    return token


async def _request(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    *,
    token: str,
    json_body: dict | None = None,
    params: dict | None = None,
) -> httpx.Response:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    return await client.request(
        method,
        f"{VERCEL_API}{path}",
        headers=headers,
        json=json_body,
        params=params,
        timeout=60.0,
    )


async def _get_project(client: httpx.AsyncClient, token: str) -> dict | None:
    resp = await _request(client, "GET", f"/v9/projects/{PROJECT_NAME}", token=token)
    if resp.status_code == 200:
        return resp.json()
    if resp.status_code == 404:
        return None
    raise RuntimeError(f"GET project HTTP {resp.status_code}: {resp.text[:400]}")


async def _create_project(
    client: httpx.AsyncClient,
    token: str,
    *,
    link_github: bool = True,
) -> dict:
    body: dict = {
        "name": PROJECT_NAME,
        "framework": "nextjs",
        "environmentVariables": [
            {
                "key": "VITRINE_BACKEND_URL",
                "value": BACKEND_URL,
                "target": ["production", "preview", "development"],
                "type": "plain",
            },
        ],
    }
    if link_github:
        body["gitRepository"] = {"type": "github", "repo": GITHUB_REPO}
    resp = await _request(client, "POST", "/v11/projects", token=token, json_body=body)
    if resp.status_code >= 400:
        raise RuntimeError(f"CREATE project HTTP {resp.status_code}: {resp.text[:600]}")
    return resp.json()


async def _link_github_repo(client: httpx.AsyncClient, token: str, project_id: str) -> None:
    resp = await _request(
        client,
        "PATCH",
        f"/v9/projects/{project_id}",
        token=token,
        json_body={"gitRepository": {"type": "github", "repo": GITHUB_REPO}},
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"LINK github HTTP {resp.status_code}: {resp.text[:600]}")


async def _upsert_env(client: httpx.AsyncClient, token: str, project_id: str) -> None:
    body = {
        "key": "VITRINE_BACKEND_URL",
        "value": BACKEND_URL,
        "type": "plain",
        "target": ["production", "preview", "development"],
    }
    resp = await _request(
        client,
        "POST",
        f"/v10/projects/{project_id}/env",
        token=token,
        json_body=body,
        params={"upsert": "true"},
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"ENV upsert HTTP {resp.status_code}: {resp.text[:400]}")


async def main() -> None:
    token = _token()
    async with httpx.AsyncClient() as client:
        existing = await _get_project(client, token)
        if existing:
            project_id = existing.get("id") or PROJECT_NAME
            print(f"EXISTS project={PROJECT_NAME} id={project_id}")
            await _upsert_env(client, token, project_id)
            print(f"ENV VITRINE_BACKEND_URL={BACKEND_URL}")
            link = existing.get("link")
            if link:
                print("link", json.dumps(link)[:200])
            return

        try:
            created = await _create_project(client, token, link_github=True)
        except RuntimeError as exc:
            if "GitHub integration" not in str(exc):
                raise
            print("GitHub App Vercel requis — création sans lien, puis liaison…")
            print("Installez https://github.com/apps/vercel sur mathiasgibiard-dotcom/vitrines")
            created = await _create_project(client, token, link_github=False)
            try:
                await _link_github_repo(client, token, created["id"])
                print("GitHub lié:", GITHUB_REPO)
            except RuntimeError as link_exc:
                print("WARN liaison GitHub:", link_exc)
        print(f"CREATED project={created.get('name')} id={created.get('id')}")
        print(f"ENV VITRINE_BACKEND_URL={BACKEND_URL}")
        print(f"Dashboard: https://vercel.com/{created.get('accountId', '')}/{PROJECT_NAME}")


if __name__ == "__main__":
    asyncio.run(main())

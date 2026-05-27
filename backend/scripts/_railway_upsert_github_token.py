"""Ajoute GITHUB_TOKEN sur Railway (service cyberforge-backend)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

import httpx

import config  # noqa: F401
from config import get_settings, plain_secret_str

GRAPHQL = "https://backboard.railway.com/graphql/v2"
PROJECT_ID = "2e4a2e4a-b2d9-4506-bbec-5d5471aabdc5"
SERVICE_ID = "43b828eb-dec4-44e5-b786-0035fd0deb4b"
ENVIRONMENT_ID = "efeaa99f-7145-4ee8-8759-c29206f821a7"


def _github_token() -> str:
    settings = get_settings()
    token = plain_secret_str(getattr(settings, "github_token", None))
    if token:
        return token
    env_path = _BACKEND / ".env"
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("GITHUB_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("GITHUB_TOKEN introuvable dans backend/.env")


def gql(query: str, variables: dict) -> dict:
    token = plain_secret_str(get_settings().railway_api_key)
    if not token:
        raise SystemExit("RAILWAY_API_KEY manquante")
    resp = httpx.post(
        GRAPHQL,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"query": query, "variables": variables},
        timeout=60.0,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("errors"):
        raise RuntimeError(json.dumps(data["errors"], indent=2))
    return data["data"]


def main() -> None:
    github_token = _github_token()
    data = gql(
        """
        mutation($input: VariableUpsertInput!) {
          variableUpsert(input: $input)
        }
        """,
        {
            "input": {
                "projectId": PROJECT_ID,
                "environmentId": ENVIRONMENT_ID,
                "serviceId": SERVICE_ID,
                "name": "GITHUB_TOKEN",
                "value": github_token,
            }
        },
    )
    print("variableUpsert GITHUB_TOKEN:", data["variableUpsert"])


if __name__ == "__main__":
    main()


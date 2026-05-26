"""
Test live upsert-hashes : affiche digest + JSON brut Cloudflare (sans secrets).
Usage: cd backend && python scripts/test_cloudflare_upsert_live.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from config import load_env_files
from security.cloudflare_env import load_cloudflare_from_env
from tools.cloudflare_pages import (
    API_BASE,
    _file_digest,
    _manifest_path,
    pages_project_name_for_token,
)

SAMPLE_HTML = "<html><body>cloudflare-upsert-test</body></html>"


async def main() -> None:
    load_env_files()
    load_cloudflare_from_env()
    from config import get_settings, plain_secret_str
    from tools.cloudflare_pages import _ensure_project

    settings = get_settings()
    account_id = plain_secret_str(settings.cloudflare_account_id).strip()
    api_token = plain_secret_str(settings.cloudflare_api_token).strip()
    if not account_id or not api_token:
        print("ERREUR: CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN manquants dans backend/.env")
        sys.exit(1)

    body = SAMPLE_HTML.encode("utf-8")
    path = "index.html"
    digest = _file_digest(path, body)
    manifest_path = _manifest_path(path)
    project_name = pages_project_name_for_token("test-upsert-live")

    print("=== Hash (Wrangler) ===")
    print(f"path:          {path}")
    print(f"manifest_path: {manifest_path}")
    print(f"digest (32):   {digest}")
    print(f"digest len:    {len(digest)}")
    print()

    headers_api = {"Authorization": f"Bearer {api_token}"}

    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=15.0)) as client:
        await _ensure_project(
            client,
            account_id=account_id,
            api_token=api_token,
            project_name=project_name,
        )

        # upload-token
        token_url = (
            f"{API_BASE}/accounts/{account_id}/pages/projects/"
            f"{project_name}/upload-token"
        )
        r_token = await client.get(token_url, headers=headers_api)
        print("=== GET upload-token ===")
        print(f"HTTP {r_token.status_code}")
        print(json.dumps(r_token.json(), indent=2, ensure_ascii=False)[:2000])
        print()

        token_payload = r_token.json()
        if not token_payload.get("success"):
            sys.exit(1)
        jwt = (token_payload.get("result") or {}).get("jwt") or ""
        if not jwt:
            print("ERREUR: jwt manquant")
            sys.exit(1)

        # upload asset
        upload_url = f"{API_BASE}/pages/assets/upload"
        upload_body = [
            {
                "key": digest,
                "value": __import__("base64").b64encode(body).decode("ascii"),
                "metadata": {"contentType": "text/html; charset=utf-8"},
                "base64": True,
            }
        ]
        r_upload = await client.post(
            upload_url,
            headers={"Authorization": f"Bearer {jwt}"},
            json=upload_body,
        )
        print("=== POST pages/assets/upload ===")
        print(f"HTTP {r_upload.status_code}")
        print(json.dumps(r_upload.json(), indent=2, ensure_ascii=False))
        print()

        # upsert-hashes (cible de l'erreur UI)
        upsert_url = f"{API_BASE}/pages/assets/upsert-hashes"
        r_upsert = await client.post(
            upsert_url,
            headers={"Authorization": f"Bearer {jwt}"},
            json={"hashes": [digest]},
        )
        print("=== POST pages/assets/upsert-hashes ===")
        print(f"HTTP {r_upsert.status_code}")
        upsert_json = r_upsert.json()
        print(json.dumps(upsert_json, indent=2, ensure_ascii=False))
        print()
        print("=== Analyse upsert ===")
        print(f"success: {upsert_json.get('success')!r}")
        print(f"result type: {type(upsert_json.get('result')).__name__}")
        print(f"result value: {upsert_json.get('result')!r}")
        print(f"errors: {upsert_json.get('errors')!r}")
        print(f"messages: {upsert_json.get('messages')!r}")


if __name__ == "__main__":
    asyncio.run(main())

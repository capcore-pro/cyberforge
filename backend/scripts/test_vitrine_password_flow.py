"""
E2E-ish test: create managed vitrine, wait deployed, validate password flow.

It exercises:
- CyberForge admin endpoints (managed vitrines + auth settings)
- Vitrine live URL behavior (middleware redirect to /auth when enabled)
- Unlock cookie flow + change password + forgot password (email via Brevo)
"""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

import config  # noqa: F401
from config import get_settings


PROMPT = (
    "Site vitrine pour 'Boulangerie Le Fournil' à Nantes. "
    "Produits: pain au levain, viennoiseries, commandes. Style moderne et chaleureux."
)


@dataclass
class Created:
    project_id: str
    slug: str


async def _api(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    *,
    json_body: dict | None = None,
    timeout: float = 60.0,
) -> httpx.Response:
    settings = get_settings()
    # Prefer the public Railway backend for a real end-to-end validation.
    base = (settings.demo_api_base_url or settings.backend_public_url or "http://127.0.0.1:8002").rstrip("/")
    url = f"{base}{path}"
    return await client.request(method, url, json=json_body, timeout=timeout)


async def create_vitrine(client: httpx.AsyncClient) -> Created:
    slug = "pwtest-" + datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S")
    r = await _api(
        client,
        "POST",
        "/api/managed-projects/vitrines",
        json_body={"prompt": PROMPT, "slug": slug},
        timeout=120.0,
    )
    r.raise_for_status()
    data = r.json()
    project_id = data["project"]["id"]
    return Created(project_id=project_id, slug=slug)


async def wait_deployed(client: httpx.AsyncClient, project_id: str, *, timeout_s: float = 420.0) -> dict:
    deadline = timeout_s
    elapsed = 0.0
    while elapsed < deadline:
        r = await _api(client, "GET", f"/api/managed-projects/vitrines/{project_id}")
        r.raise_for_status()
        proj = r.json()
        status = proj.get("status")
        if status in ("deployed", "failed"):
            return proj
        await asyncio.sleep(5.0)
        elapsed += 5.0
    raise RuntimeError("Timeout waiting for deployed/failed.")


async def set_auth(
    client: httpx.AsyncClient,
    project_id: str,
    *,
    enabled: bool,
    client_email: str,
    generate_password: bool,
) -> dict:
    r = await _api(
        client,
        "POST",
        f"/api/managed-projects/vitrines/{project_id}/auth",
        json_body={
            "enabled": enabled,
            "client_email": client_email,
            "generate_password": generate_password,
        },
    )
    r.raise_for_status()
    return r.json()


async def _fetch_no_follow(client: httpx.AsyncClient, url: str) -> httpx.Response:
    return await client.get(url, follow_redirects=False, timeout=30.0, headers={"User-Agent": "CyberForge/test"})


async def validate_site_flow(url_production: str, password: str, client_email: str) -> None:
    async with httpx.AsyncClient() as client:
        # 1) should redirect to /auth when enabled
        r = await _fetch_no_follow(client, url_production)
        if r.status_code not in (301, 302, 303, 307, 308):
            raise RuntimeError(f"Expected redirect to /auth, got {r.status_code}")
        loc = r.headers.get("location", "")
        if "/auth" not in loc:
            raise RuntimeError(f"Expected /auth redirect, got location={loc!r}")

        # 2) unlock via site endpoint => cookie set
        unlock = await client.post(
            url_production.rstrip("/") + "/api/auth/unlock",
            json={"password": password},
            timeout=30.0,
        )
        unlock.raise_for_status()
        if not unlock.json().get("ok"):
            raise RuntimeError("Unlock failed.")

        # 3) now homepage should be 200
        ok = await client.get(url_production, timeout=30.0)
        if ok.status_code >= 400:
            raise RuntimeError(f"Expected 2xx after unlock, got {ok.status_code}")

        # 4) change password
        new_pwd = password + "9"
        ch = await client.post(
            url_production.rstrip("/") + "/api/auth/change-password",
            json={"current_password": password, "new_password": new_pwd},
            timeout=30.0,
        )
        ch.raise_for_status()
        if not ch.json().get("ok"):
            raise RuntimeError("Change password failed.")

        # 5) forgot password (email)
        fp = await client.post(
            url_production.rstrip("/") + "/api/auth/forgot-password",
            json={"email": client_email},
            timeout=30.0,
        )
        fp.raise_for_status()
        if not fp.json().get("ok"):
            raise RuntimeError("Forgot password returned ok=false.")


async def main() -> None:
    settings = get_settings()
    print("Backend base:", settings.demo_api_base_url or settings.backend_public_url)
    async with httpx.AsyncClient() as client:
        created = await create_vitrine(client)
        print("Created:", created.slug, created.project_id)

        proj = await wait_deployed(client, created.project_id)
        print("Status:", proj.get("status"))
        if proj.get("status") != "deployed":
            raise RuntimeError(f"Deploy failed: {json.dumps(proj, indent=2)[:2000]}")

        url_prod = proj.get("url_production")
        if not url_prod:
            raise RuntimeError("Missing url_production.")
        print("Production:", url_prod)

        auth = await set_auth(
            client,
            created.project_id,
            enabled=True,
            client_email=(settings.capcore_notify_email or "capcore.pro@gmail.com"),
            generate_password=True,
        )
        pwd = auth.get("password")
        if not pwd:
            raise RuntimeError("Missing generated password.")
        print("Password:", pwd)

        await validate_site_flow(url_prod, pwd, auth.get("client_email") or "")
        print("OK: password flow validated")


if __name__ == "__main__":
    asyncio.run(main())


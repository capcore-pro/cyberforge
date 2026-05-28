"""
E2E test for managed application_web (split Railway backend + Vercel frontend).
"""

from __future__ import annotations

import time

import httpx

BASE = "https://cyberforge-backend-production.up.railway.app"


def main() -> None:
    slug = f"appwebtest-{int(time.time())}"
    prompt = "Application web test: dashboard + health check. (CyberForge managed application_web)"
    c = httpx.Client(timeout=90.0)

    r = c.post(f"{BASE}/api/managed-projects/application-web", json={"prompt": prompt, "slug": slug})
    r.raise_for_status()
    pid = r.json()["project"]["id"]
    print("created", slug, pid)

    # Wait deploy
    for _ in range(120):
        rr = c.get(f"{BASE}/api/managed-projects/application-web/{pid}")
        rr.raise_for_status()
        row = rr.json()
        st = row.get("status")
        if st in ("deployed", "failed"):
            print("status", st)
            if st == "failed":
                raise SystemExit(row.get("error_last"))
            break
        time.sleep(5)

    row = c.get(f"{BASE}/api/managed-projects/application-web/{pid}").json()
    print("frontend", row.get("url_production"))
    print("backend", row.get("url_backend"))
    assert row.get("url_production", "").startswith("https://"), "missing frontend url"
    assert row.get("url_backend", "").startswith("https://"), "missing backend url"

    # Update (should redeploy)
    upd = c.post(f"{BASE}/api/managed-projects/application-web/{pid}/update", json={"prompt": prompt + " update"})
    upd.raise_for_status()
    print("update scheduled")

    # Hard delete
    d = c.post(f"{BASE}/api/managed-projects/application-web/{pid}/delete", json={"hard_delete": True})
    d.raise_for_status()
    print("hard delete requested")

    # Poll deleted
    for _ in range(60):
        rr = c.get(f"{BASE}/api/managed-projects/application-web/{pid}")
        if rr.status_code == 404:
            print("gone")
            break
        row = rr.json()
        if row.get("status") == "deleted":
            print("deleted")
            break
        time.sleep(5)

    runs = c.get(f"{BASE}/api/managed-projects/application-web/{pid}/runs")
    runs.raise_for_status()
    print("runs", runs.json()[:1])


if __name__ == "__main__":
    main()


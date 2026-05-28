"""
E2E: create extension_navigateur → wait ready → download zip → validate.
"""

from __future__ import annotations

import io
import time
import zipfile

import httpx

BASE = "https://cyberforge-backend-production.up.railway.app"


def main() -> None:
    slug = f"exttest-{int(time.time())}"
    prompt = "Extension MV3 simple: popup compteur + background log."
    c = httpx.Client(timeout=90.0)

    r = c.post(f"{BASE}/api/managed-projects/extensions", json={"prompt": prompt, "slug": slug})
    r.raise_for_status()
    pid = r.json()["project"]["id"]
    print("created", slug, pid)

    for _ in range(60):
        row = c.get(f"{BASE}/api/managed-projects/extensions/{pid}").json()
        st = row.get("status")
        if st in ("deployed", "failed"):
            print("status", st)
            if st == "failed":
                raise SystemExit(row.get("error_last"))
            break
        time.sleep(1.5)

    z = c.get(f"{BASE}/api/managed-projects/extensions/{pid}/artifact.zip")
    z.raise_for_status()
    assert z.headers.get("content-type", "").startswith("application/zip")
    data = z.content
    print("zip_bytes", len(data))

    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = set(archive.namelist())
        required = {"manifest.json", "popup.html", "popup.js", "background.js", "README.md"}
        missing = required - names
        assert not missing, f"missing files: {missing}"
        manifest = archive.read("manifest.json").decode("utf-8")
        assert "\"manifest_version\": 3" in manifest
    print("ok")


if __name__ == "__main__":
    main()


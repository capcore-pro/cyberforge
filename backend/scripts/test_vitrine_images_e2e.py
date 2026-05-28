"""
E2E: search Unsplash → replace hero image → wait deployed → verify content/site.json changed on GitHub.
"""

from __future__ import annotations

import base64
import os
import time

import httpx
from dotenv import load_dotenv

BASE = (os.environ.get("BASE_URL") or "http://127.0.0.1:8003").rstrip("/")


def gh_get_file(repo: str, branch: str, path: str, token: str) -> str:
    owner, name = repo.split("/", 1)
    url = f"https://api.github.com/repos/{owner}/{name}/contents/{path.lstrip('/')}"
    r = httpx.get(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        params={"ref": branch},
        timeout=30.0,
    )
    r.raise_for_status()
    js = r.json()
    raw = base64.b64decode(js["content"].encode("utf-8"))
    return raw.decode("utf-8")


def main() -> None:
    load_dotenv("backend/.env", override=False)
    gh_token = os.environ.get("GITHUB_TOKEN", "")
    if not gh_token:
        raise SystemExit("Missing GITHUB_TOKEN for verification.")

    c = httpx.Client(timeout=90.0)
    # Prefer reusing an existing deployed vitrine (avoids Vercel/GitHub integration constraints in some envs).
    pid = None
    slug = None
    repo = None
    l = c.get(f"{BASE}/api/managed-projects/vitrines")
    if l.status_code < 400:
        rows = l.json()
        if isinstance(rows, list):
            for row in rows:
                if row.get("status") == "deployed" and row.get("github_repo") and row.get("github_branch"):
                    pid = row.get("id")
                    slug = row.get("github_branch")
                    repo = row.get("github_repo")
                    break

    if not pid:
        slug = f"imgtest-{int(time.time())}"
        prompt = "Vitrine test image picker (plombier, hero photo)."
        r = c.post(f"{BASE}/api/managed-projects/vitrines", json={"prompt": prompt, "slug": slug})
        r.raise_for_status()
        pid = r.json()["project"]["id"]
        print("created", slug, pid)
    else:
        print("reusing", slug, pid)

    # Wait initial deploy
    branch = slug
    error_last = None
    for _ in range(120):
        row = c.get(f"{BASE}/api/managed-projects/vitrines/{pid}").json()
        st = row.get("status")
        repo = row.get("github_repo") or repo
        error_last = row.get("error_last")
        if st in ("deployed", "failed"):
            print("status", st)
            break
        time.sleep(2.0)

    # If Vercel complains about missing git branch, retry once via update after a short delay
    if row.get("status") == "failed" and isinstance(error_last, str) and "git_branch_not_found" in error_last:
        print("retry_update_after_branch_not_found")
        time.sleep(6.0)
        u = c.post(f"{BASE}/api/managed-projects/vitrines/{pid}/update", json={"prompt": prompt})
        u.raise_for_status()
        for _ in range(120):
            row = c.get(f"{BASE}/api/managed-projects/vitrines/{pid}").json()
            st = row.get("status")
            if st in ("deployed", "failed"):
                print("status_retry", st)
                if st == "failed":
                    raise SystemExit(row.get("error_last"))
                break
            time.sleep(2.0)
    elif row.get("status") == "failed":
        raise SystemExit(error_last or "provision failed")

    assert repo
    before = gh_get_file(repo, branch, "content/site.json", gh_token)

    # Search
    s = c.get(
        f"{BASE}/api/managed-projects/vitrines/{pid}/images/search",
        params={"q": "plombier", "orientation": "landscape", "page": 1},
    )
    s.raise_for_status()
    results = s.json()
    assert isinstance(results, list) and results, "no unsplash results"
    pick = results[0]

    # Set hero
    up = c.post(
        f"{BASE}/api/managed-projects/vitrines/{pid}/images/set",
        json={
            "slot": "hero",
            "url": pick["url"],
            "alt": pick["alt"],
            "photographer": pick.get("photographer"),
            "photographerUrl": pick.get("photographerUrl"),
            "imageQuery": pick.get("imageQuery") or "plombier",
        },
    )
    up.raise_for_status()

    # Wait redeploy
    for _ in range(120):
        row = c.get(f"{BASE}/api/managed-projects/vitrines/{pid}").json()
        st = row.get("status")
        if st in ("deployed", "failed"):
            print("status_after", st)
            if st == "failed":
                raise SystemExit(row.get("error_last"))
            break
        time.sleep(2.0)

    after = gh_get_file(repo, branch, "content/site.json", gh_token)
    assert before != after, "site.json did not change"
    assert pick["url"] in after, "new image url not found in site.json"
    print("ok")


if __name__ == "__main__":
    main()


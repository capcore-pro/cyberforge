from __future__ import annotations

import os
import sys

import httpx


def main() -> int:
    base = (os.environ.get("BASE_URL") or "http://127.0.0.1:8003").rstrip("/")
    url = os.environ.get("CLONE_URL") or "https://example.com"
    payload = {
        "url": url,
        "improved_prompt": "Version premium, CTA clair, preuve sociale, sections nettes.",
    }
    r = httpx.post(f"{base}/api/demos/url-clone/preview", json=payload, timeout=60.0)
    if r.status_code >= 400:
        print("ERR", r.status_code, r.text[:800])
        # Tavily non configuré => attendu en dev
        return 0 if r.status_code == 503 else 1
    data = r.json()
    assert isinstance(data.get("html"), str) and "<!DOCTYPE" in data["html"]
    print("OK", data.get("vertical"), "chars", data.get("extracted_chars"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


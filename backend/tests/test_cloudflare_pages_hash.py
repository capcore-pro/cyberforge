"""Hash Direct Upload aligné sur Wrangler (workers-sdk pages/hash.ts)."""

from __future__ import annotations

import base64

import blake3

from tools.cloudflare_pages import _file_digest, _manifest_path


def test_file_digest_matches_wrangler_formula() -> None:
    body = b"<html><body>demo</body></html>"
    path = "index.html"
    b64 = base64.b64encode(body).decode("ascii")
    expected = blake3.blake3((b64 + "html").encode("utf-8")).hexdigest()[:32]
    assert _file_digest(path, body) == expected


def test_manifest_path_leading_slash() -> None:
    assert _manifest_path("index.html") == "/index.html"
    assert _manifest_path("\\assets\\app.js") == "/assets/app.js"

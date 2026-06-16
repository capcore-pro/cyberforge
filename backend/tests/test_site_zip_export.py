"""Tests export ZIP site complet."""

from __future__ import annotations

import io
import zipfile
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from api.main import create_app
from tools.site_zip_export import (
    build_site_export_zip,
    extract_inline_scripts,
    extract_inline_styles,
    prepare_site_export_files,
)


SAMPLE_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <title>Demo</title>
  <style>
    body { background: #111; color: #fff; }
    h1 { color: gold; }
  </style>
  <script src="https://cdn.example.com/lib.js"></script>
</head>
<body>
  <h1>Hello</h1>
  <script>
    console.log("inline");
    document.title = "OK";
  </script>
</body>
</html>
"""


def test_extract_inline_styles_removes_style_tags() -> None:
    html, css = extract_inline_styles(SAMPLE_HTML)
    assert "<style" not in html.lower()
    assert "background: #111" in css
    assert "color: gold" in css


def test_extract_inline_scripts_keeps_external_src() -> None:
    html, js = extract_inline_scripts(SAMPLE_HTML)
    assert 'src="https://cdn.example.com/lib.js"' in html
    assert "console.log" in js
    assert "console.log" not in html


def test_prepare_site_export_files_structure() -> None:
    fixed = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)
    files = prepare_site_export_files(
        SAMPLE_HTML,
        "Mon Projet Test",
        on_date=fixed,
    )
    assert "index.html" in files
    assert "assets/style.css" in files
    assert "assets/script.js" in files
    assert "assets/README.txt" in files
    assert '<link rel="stylesheet" href="assets/style.css">' in files["index.html"]
    assert '<script src="assets/script.js"></script>' in files["index.html"]
    assert "<style" not in files["index.html"].lower()
    assert "CyberForge" in files["assets/README.txt"]


def test_build_site_export_zip_contains_entries() -> None:
    fixed = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)
    zip_bytes, filename = build_site_export_zip(
        SAMPLE_HTML,
        "Mon Projet Test",
        on_date=fixed,
    )
    assert filename == "mon-projet-test-2026-06-16.zip"
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        names = set(archive.namelist())
    assert names == {
        "index.html",
        "assets/README.txt",
        "assets/script.js",
        "assets/style.css",
    }


def test_export_zip_route_returns_zip() -> None:
    client = TestClient(create_app())
    with patch("api.routes.editor.get_supabase_store") as mock_store:
        store = MagicMock()
        store.is_configured.return_value = True
        store.get_editor_html = AsyncMock(
            return_value={
                "generation_id": "gen-1",
                "html": SAMPLE_HTML,
                "project_title": "Mon Projet Test",
            }
        )
        mock_store.return_value = store
        with patch(
            "api.routes.editor.build_site_export_zip",
            wraps=build_site_export_zip,
        ) as mock_build:
            fixed = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)
            mock_build.side_effect = lambda html, title, **kwargs: build_site_export_zip(
                html,
                title,
                on_date=fixed,
                **kwargs,
            )
            res = client.get("/api/editor/proj-1/export-zip")

    assert res.status_code == 200
    assert res.headers["content-type"] == "application/zip"
    assert "mon-projet-test-2026-06-16.zip" in res.headers.get(
        "content-disposition", ""
    )
    with zipfile.ZipFile(io.BytesIO(res.content)) as archive:
        assert "index.html" in archive.namelist()
        index = archive.read("index.html").decode("utf-8")
        css = archive.read("assets/style.css").decode("utf-8")
    assert "<style" not in index.lower()
    assert "background: #111" in css

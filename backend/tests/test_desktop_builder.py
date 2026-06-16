"""Tests Desktop Builder — ElectronAI, ZIP package, routes."""

from __future__ import annotations

import asyncio
import io
import zipfile
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from agents.electron_ai import build_electron_files, run as electron_run
from api.main import create_app
from tools.desktop_zip_export import build_desktop_package_zip

SAMPLE_HTML = """<!DOCTYPE html>
<html><head><title>App</title></head>
<body><h1>Dashboard</h1></body></html>
"""


def test_electron_run_returns_required_files() -> None:
    result = asyncio.run(
        electron_run("Logiciel de facturation artisan", SAMPLE_HTML, {})
    )
    files = result["files"]
    assert "main.js" in files
    assert "preload.js" in files
    assert "package.json" in files
    assert "instructions_build.md" in files
    assert "BrowserWindow" in files["main.js"]
    assert "contextBridge" in files["preload.js"]
    assert "electron-builder" in files["package.json"]
    assert "npm run build" in files["instructions_build.md"]


def test_build_desktop_package_zip_contains_entries() -> None:
    files = build_electron_files("Mon App Desktop")
    zip_bytes, filename = build_desktop_package_zip(SAMPLE_HTML, files, "Mon App")
    assert filename.endswith(".zip")
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        names = set(archive.namelist())
        index = archive.read("index.html").decode("utf-8")
    assert "index.html" in names
    assert "main.js" in names
    assert "preload.js" in names
    assert "package.json" in names
    assert "instructions_build.md" in names
    assert "Dashboard" in index


def test_download_desktop_route_returns_zip() -> None:
    client = TestClient(create_app())
    electron_files = build_electron_files("Facture Express")
    with patch("api.routes.editor.get_supabase_store") as mock_store:
        store = MagicMock()
        store.is_configured.return_value = True
        store.get_editor_html = AsyncMock(
            return_value={
                "generation_id": "gen-1",
                "html": SAMPLE_HTML,
                "project_title": "Facture Express",
                "project_type": "application_desktop",
                "is_desktop": True,
                "electron_files": electron_files,
            }
        )
        mock_store.return_value = store
        res = client.get("/api/editor/proj-1/download-desktop")

    assert res.status_code == 200
    assert res.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(res.content)) as archive:
        assert "main.js" in archive.namelist()
        assert "index.html" in archive.namelist()


def test_deploy_ai_desktop_packages_zip() -> None:
    asyncio.run(_test_deploy_ai_desktop_packages_zip())


async def _test_deploy_ai_desktop_packages_zip() -> None:
    from agents.deploy_ai import DeployAI

    with patch("media_storage.sync_to_r2", return_value="https://cdn.example.com/pkg.zip"):
        deploy = DeployAI()
        result = await deploy.run(
            SAMPLE_HTML,
            title="Facture Express",
            project_type="application_desktop",
            brief={
                "electron_files": build_electron_files("Facture Express"),
                "description": "Facture Express",
            },
        )

    assert result["success"] is True
    assert result.get("desktop_package") is True
    assert result["url"] == "https://cdn.example.com/pkg.zip"
    assert "electron_files" in result

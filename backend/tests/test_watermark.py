"""Tests watermark CyberForge — injection, suppression, déploiement, export."""

from __future__ import annotations

import io
import zipfile
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from api.main import create_app
from tools.site_zip_export import build_site_export_zip
from tools.watermark import (
    inject_expiry_banner,
    inject_watermark,
    remove_watermark,
)

SAMPLE_HTML = """<!DOCTYPE html>
<html><head><title>Demo</title></head>
<body><h1>Hello</h1></body>
</html>
"""

SAMPLE_HTML_NO_BODY = "<html><head></head><h1>Hi</h1></html>"


def test_inject_watermark_before_body_close() -> None:
    out = inject_watermark(SAMPLE_HTML)
    assert 'id="cyberforge-watermark"' in out
    assert out.index("cyberforge-watermark") < out.lower().index("</body>")


def test_inject_watermark_appends_without_body_close() -> None:
    out = inject_watermark(SAMPLE_HTML_NO_BODY)
    assert 'id="cyberforge-watermark"' in out
    assert out.index("cyberforge-watermark") > out.index("<h1>")


def test_remove_watermark_cleans_injected_html() -> None:
    watermarked = inject_watermark(SAMPLE_HTML)
    assert 'id="cyberforge-watermark"' in watermarked
    clean = remove_watermark(watermarked)
    assert "cyberforge-watermark" not in clean
    assert "<h1>Hello</h1>" in clean


def test_inject_expiry_banner_after_body() -> None:
    out = inject_expiry_banner(SAMPLE_HTML, "20 juin 2026")
    assert 'id="cyberforge-expiry"' in out
    assert "20 juin 2026" in out
    assert out.lower().index("<body") < out.index("cyberforge-expiry")


def test_remove_watermark_removes_expiry_banner() -> None:
    html = inject_expiry_banner(SAMPLE_HTML, "20 juin 2026")
    clean = remove_watermark(html)
    assert "cyberforge-expiry" not in clean


def test_build_site_export_zip_strips_watermark() -> None:
    watermarked = inject_watermark(SAMPLE_HTML)
    zip_bytes, _filename = build_site_export_zip(watermarked, "Projet Test")
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        index = archive.read("index.html").decode("utf-8")
    assert "cyberforge-watermark" not in index
    assert "<h1>Hello</h1>" in index


def test_export_zip_route_returns_zip_without_watermark() -> None:
    client = TestClient(create_app())
    watermarked = inject_watermark(SAMPLE_HTML)
    with patch("api.routes.editor.get_supabase_store") as mock_store:
        store = MagicMock()
        store.is_configured.return_value = True
        store.get_editor_html = AsyncMock(
            return_value={
                "generation_id": "gen-1",
                "html": watermarked,
                "project_title": "Mon Projet Test",
            }
        )
        mock_store.return_value = store
        res = client.get("/api/editor/proj-1/export-zip")

    assert res.status_code == 200
    with zipfile.ZipFile(io.BytesIO(res.content)) as archive:
        index = archive.read("index.html").decode("utf-8")
    assert "cyberforge-watermark" not in index


def test_deploy_ai_injects_watermark_before_upload() -> None:
    import asyncio
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "agents" / "deploy_ai.py"
    spec = importlib.util.spec_from_file_location("deploy_ai_watermark_test", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    async def _run() -> None:
        with (
            patch.object(mod, "inject_pexels_images", new_callable=AsyncMock) as mock_pexels,
            patch.object(mod, "deploy_html_demo", new_callable=AsyncMock) as mock_deploy,
        ):
            mock_pexels.return_value = SAMPLE_HTML
            mock_deploy.return_value = (
                "https://demo.pages.dev/x",
                "tok",
                "pwd",
                "https://demo.pages.dev/x/unlock",
            )
            agent = mod.DeployAI()
            await agent.run(SAMPLE_HTML, title="Test")

            mock_deploy.assert_awaited_once()
            deployed_html = mock_deploy.await_args.kwargs.get("html") or mock_deploy.await_args.args[0]
            assert 'id="cyberforge-watermark"' in deployed_html

    asyncio.run(_run())


def test_redeploy_remove_watermark_route() -> None:
    client = TestClient(create_app())
    watermarked = inject_watermark(SAMPLE_HTML)

    with (
        patch("api.routes.editor.get_supabase_store") as mock_store,
        patch("api.routes.editor.deploy_html_demo", new_callable=AsyncMock) as mock_deploy,
        patch("api.routes.editor.get_audit_store") as mock_audit_get,
    ):
        store = MagicMock()
        store.is_configured.return_value = True
        store.get_editor_html = AsyncMock(
            return_value={
                "generation_id": "gen-1",
                "html": watermarked,
                "project_type": "vitrine_next",
                "project_title": "Projet",
            }
        )
        store.save_editor_html = AsyncMock()
        store.update_project_demo_url = AsyncMock()
        mock_store.return_value = store

        mock_deploy.return_value = (
            "https://demo.pages.dev/x",
            "tok",
            "pwd",
            "https://demo.pages.dev/x",
        )

        audit = MagicMock()
        audit.log = AsyncMock()
        mock_audit_get.return_value = audit

        res = client.post(
            "/api/editor/proj-1/redeploy",
            json={
                "generation_id": "gen-1",
                "html": watermarked,
                "remove_watermark": True,
            },
        )

    assert res.status_code == 200
    deployed_html = mock_deploy.await_args.kwargs.get("html") or mock_deploy.await_args.args[0]
    assert "cyberforge-watermark" not in deployed_html
    audit.log.assert_any_await(
        "watermark_removed",
        project_id="proj-1",
        event_data={
            "generation_id": "gen-1",
            "url": "https://demo.pages.dev/x",
        },
    )

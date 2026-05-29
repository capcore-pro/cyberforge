"""Tests API médiathèque."""

from __future__ import annotations

import importlib
import io
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from tools import media_library


@pytest.fixture()
def media_client(monkeypatch: pytest.MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        media_dir = Path(tmp) / "media"
        db_path = Path(tmp) / "cockpit.db"
        monkeypatch.setenv("MEDIA_ROOT", str(media_dir))
        monkeypatch.setattr("cockpit_db._DB_PATH", db_path)

        import cockpit_db
        import media_db
        import media_storage
        import media_router

        importlib.reload(cockpit_db)
        importlib.reload(media_db)
        importlib.reload(media_storage)
        importlib.reload(media_router)

        cockpit_db.init_db()
        app = create_app()
        app.include_router(media_router.router, prefix="/api/media")
        with TestClient(app) as client:
            yield client, media_router


def test_upload_and_serve_file(media_client) -> None:
    client, _router = media_client
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n\x2d\xb4"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    res = client.post(
        "/api/media/upload",
        files={"file": ("test.png", io.BytesIO(png), "image/png")},
        data={"tags": '["test"]'},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["type"] == "image"
    assert body["local_url"].startswith("/api/media/files/")

    file_res = client.get(f"/api/media/files/{body['id']}")
    assert file_res.status_code == 200
    assert file_res.content == png


def test_list_and_delete_asset(media_client) -> None:
    client, _router = media_client
    res = client.post(
        "/api/media/upload",
        files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
    )
    assert res.status_code == 201
    asset_id = res.json()["id"]

    listed = client.get("/api/media/assets", params={"type": "pdf"})
    assert listed.status_code == 200
    assert any(a["id"] == asset_id for a in listed.json())

    detail = client.get(f"/api/media/assets/{asset_id}")
    assert detail.status_code == 200

    deleted = client.delete(f"/api/media/assets/{asset_id}")
    assert deleted.status_code == 200
    assert client.get(f"/api/media/assets/{asset_id}").status_code == 404


def test_save_generated_asset_from_bytes_url(
    media_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    import asyncio

    _client, _router_mod = media_client
    png = b"\x89PNG\r\n\x1a\n"

    class FakeResponse:
        headers = {"content-type": "image/png"}
        content = png

        def raise_for_status(self) -> None:
            return None

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args) -> None:
            return None

        async def get(self, url: str):
            return FakeResponse()

    monkeypatch.setattr(media_library.httpx, "AsyncClient", FakeAsyncClient)

    asset = asyncio.run(
        media_library.save_generated_asset(
            "https://example.com/photo.png",
            "photo.png",
            "proj-99",
            "generated",
            tags=["unsplash"],
        )
    )
    assert asset["source"] == "generated"
    assert asset["project_id"] == "proj-99"
    assert "unsplash" in asset["tags"]

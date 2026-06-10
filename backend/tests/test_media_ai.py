"""Tests MediaAI — upscale, recherche Pexels, génération (mocks)."""

from __future__ import annotations

import asyncio
import importlib
import io
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from agents.media_ai import MediaAIAgent, generate_image, search_pexels, upscale_image
from api.main import create_app


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


def test_upscale_route_creates_upscaled_asset(media_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _router = media_client
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n\x2d\xb4"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    up = client.post(
        "/api/media/upload",
        files={"file": ("test.png", io.BytesIO(png), "image/png")},
    )
    assert up.status_code == 201, up.text
    asset_id = up.json()["id"]

    async def _fake_upscale(*_args, **_kwargs):
        return {"url": "https://replicate.test/upscaled.png", "scale": 4}

    mock_agent = type("MockAgent", (), {})()
    mock_agent.upscale = AsyncMock(side_effect=_fake_upscale)
    monkeypatch.setattr("agents.media_ai.MediaAIAgent", lambda: mock_agent)

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

    import tools.media_library as ml

    monkeypatch.setattr(ml.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(
        "tools.replicate_image_gen.ReplicateImageGenerator.is_configured",
        lambda self: True,
    )

    res = client.post("/api/media/upscale", json={"asset_id": asset_id, "scale": 4})
    assert res.status_code == 201, res.text
    body = res.json()
    assert "upscaled" in body["tags"]
    assert any(t.startswith("from:") for t in body["tags"])


def test_upscale_route_503_without_replicate(media_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _router = media_client
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 40
    up = client.post(
        "/api/media/upload",
        files={"file": ("x.png", io.BytesIO(png), "image/png")},
    )
    asset_id = up.json()["id"]
    monkeypatch.setattr(
        "tools.replicate_image_gen.ReplicateImageGenerator.is_configured",
        lambda self: False,
    )
    res = client.post("/api/media/upscale", json={"asset_id": asset_id, "scale": 4})
    assert res.status_code == 503


def test_search_route_saves_pexels_assets(media_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _router = media_client

    async def _fake_search(_query: str, count: int = 12):
        return [
            {
                "url": f"https://images.pexels.com/photos/{i}/pexels-photo.jpeg",
                "thumbnail": f"https://images.pexels.com/photos/{i}/thumb.jpeg",
                "author": "Author",
                "source": "pexels",
            }
            for i in range(count)
        ]

    monkeypatch.setattr(
        "agents.media_ai.search_pexels",
        _fake_search,
    )

    class FakeResponse:
        headers = {"content-type": "image/jpeg"}
        content = b"\xff\xd8\xff" + b"\x00" * 80

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

    import tools.media_library as ml

    monkeypatch.setattr(ml.httpx, "AsyncClient", FakeAsyncClient)

    res = client.get("/api/media/search", params={"q": "boulangerie", "count": 6})
    assert res.status_code == 200, res.text
    items = res.json()
    assert len(items) == 6
    assert all("pexels" in a["tags"] for a in items)


def test_generate_hero_style_prompt() -> None:
    captured: dict[str, str] = {}

    async def _fake_gen(prompt: str, *, project_id=None):
        captured["prompt"] = prompt
        return "https://replicate.test/gen.png"

    with (
        patch("agents.media_ai._replicate_configured", return_value=True),
        patch("agents.media_ai.ReplicateImageGenerator") as gen_cls,
    ):
        gen_cls.return_value.generate_image = AsyncMock(side_effect=_fake_gen)
        result = asyncio.run(
            generate_image("café parisien", style="hero")
        )

    assert result is not None
    assert "cinematic" in result["prompt_used"]
    assert "high resolution landscape" in result["prompt_used"]


def test_generate_returns_none_without_replicate() -> None:
    with patch("agents.media_ai._replicate_configured", return_value=False):
        result = asyncio.run(generate_image("test", style="premium"))
    assert result is None


def test_upscale_returns_none_without_replicate() -> None:
    with patch("agents.media_ai._replicate_configured", return_value=False):
        result = asyncio.run(upscale_image("https://example.com/a.png", 4))
    assert result is None


def test_search_pexels_empty_without_key() -> None:
    with patch("agents.media_ai._pexels_configured", return_value=False):
        result = asyncio.run(search_pexels("boulangerie", 6))
    assert result == []


def test_media_agent_generate_wrapper() -> None:
    agent = MediaAIAgent()
    with patch(
        "agents.media_ai.generate_image",
        new=AsyncMock(return_value={"url": "https://x.test", "prompt_used": "p"}),
    ):
        result = asyncio.run(agent.generate("café", style="hero"))
    assert result and result["url"] == "https://x.test"

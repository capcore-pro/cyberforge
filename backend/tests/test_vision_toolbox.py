"""Tests VisionUI — toolbox photos, enrichissement HTML."""

import asyncio
from unittest.mock import AsyncMock, patch

from tools.toolbox_media import (
    ToolboxPhoto,
    photo_relevance_score,
    relevant_photos,
)
from tools.vision_toolbox_enricher import _inject_photos, enrich_html_with_toolbox


def test_photo_relevance_threshold() -> None:
    photos = [
        ToolboxPhoto(
            id=f"p{i}",
            url_thumb="t",
            url_full="f",
            url_download="d",
            source="pexels",
            relevance_score=photo_relevance_score("restaurant", rank=i),
        )
        for i in range(6)
    ]
    picked = relevant_photos(photos, min_count=3, min_score=0.45)
    assert len(picked) >= 3

    weak = [p.model_copy(update={"relevance_score": 0.2}) for p in photos[:2]]
    assert relevant_photos(weak, min_count=3, min_score=0.45) == []


def test_inject_photos_replaces_unsplash() -> None:
    html = (
        '<img src="https://images.unsplash.com/photo-1?w=1200" alt="hero" />'
        '<img src="https://example.com/logo.png" alt="logo" />'
    )
    out, count = _inject_photos(
        html,
        ["https://media.local/pexels_1.jpg", "https://media.local/pexels_2.jpg"],
    )
    assert count == 1
    assert "media.local/pexels_1.jpg" in out
    assert "example.com/logo.png" in out


def test_enrich_html_stock_photos(monkeypatch) -> None:
    stock = [
        ToolboxPhoto(
            id=f"pexels-{i}",
            url_thumb="t",
            url_full=f"https://images.pexels.com/{i}.jpg",
            url_download=f"https://images.pexels.com/{i}.jpg",
            source="pexels",
            relevance_score=0.9 - i * 0.05,
        )
        for i in range(4)
    ]

    async def fake_search(*args, **kwargs):
        return "restaurant interior", stock

    async def fake_persist(photo, **kwargs):
        return f"https://cdn.example/{photo.id}.jpg"

    with (
        patch(
            "tools.vision_toolbox_enricher.search_toolbox_photos",
            new=AsyncMock(side_effect=fake_search),
        ),
        patch(
            "tools.vision_toolbox_enricher._persist_photo",
            new=AsyncMock(side_effect=fake_persist),
        ),
        patch(
            "tools.vision_toolbox_enricher._inject_icons",
            new=AsyncMock(side_effect=lambda html, **kw: html),
        ),
        patch(
            "tools.vision_toolbox_enricher._inject_illustrations",
            new=AsyncMock(side_effect=lambda html, **kw: html),
        ),
    ):
        html_in = '<img src="https://images.unsplash.com/photo-1" alt="" />'
        out, stats = asyncio.run(
            enrich_html_with_toolbox(html_in, prompt="Restaurant Lyon")
        )

    assert "cdn.example/pexels-0.jpg" in out
    assert stats.photos_stock >= 1
    assert "pexels" in stats.tags

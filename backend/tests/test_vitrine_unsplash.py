"""Tests résolution images Unsplash (Phase 4.2c)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from config import Settings
from tools.vitrine.scaffold_renderer import load_example_content
from tools.vitrine.unsplash_resolver import UnsplashImageResolver, resolve_vitrine_images


def _mock_search_response() -> dict:
    return {
        "results": [
            {
                "id": "photo-1",
                "urls": {
                    "regular": "https://images.unsplash.com/photo-1?ixid=abc",
                },
                "user": {
                    "name": "Jane Doe",
                    "links": {"html": "https://unsplash.com/@jane"},
                },
                "alt_description": "Professional plumber at work",
            }
        ]
    }


def test_resolver_skips_without_api_key() -> None:
    settings = Settings(unsplash_access_key=None)
    content = load_example_content()
    original_url = content.home.hero.image.url

    resolved, stats = asyncio.run(
        resolve_vitrine_images(content, settings=settings),
    )

    assert stats.resolved == 0
    assert resolved.home.hero.image.url == original_url


def test_resolver_replaces_images_with_api_key() -> None:
    settings = Settings(unsplash_access_key="test-unsplash-key")
    content = load_example_content()
    content.home.hero.image.imageQuery = "plumber repair"

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = _mock_search_response()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("tools.vitrine.unsplash_resolver.httpx.AsyncClient", return_value=mock_client),
        patch(
            "tools.media_library.try_save_generated_asset",
            new_callable=AsyncMock,
        ),
    ):
        resolved, stats = asyncio.run(
            resolve_vitrine_images(content, settings=settings),
        )

    assert stats.resolved >= 1
    hero = resolved.home.hero.image
    assert "photo-1" in hero.url
    assert "w=1200" in hero.url
    assert hero.photographer == "Jane Doe"
    assert hero.photographerUrl == "https://unsplash.com/@jane"
    mock_client.get.assert_called()
    first_call = mock_client.get.call_args_list[0]
    assert first_call.kwargs["headers"]["Authorization"] == "Client-ID test-unsplash-key"


def test_sized_unsplash_url_adds_params() -> None:
    from tools.vitrine.unsplash_resolver import _sized_unsplash_url

    url = _sized_unsplash_url("https://images.unsplash.com/photo-1", width=800)
    assert "w=800" in url
    assert "q=80" in url


def test_resolver_configured_flag() -> None:
    assert UnsplashImageResolver(Settings(unsplash_access_key="x")).configured
    assert not UnsplashImageResolver(Settings(unsplash_access_key=None)).configured

"""Tests tracker vues démos — device detection, store, routes."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from api.main import create_app
from db.demo_tracking_store import DemoTrackingStore, detect_device_type


def test_detect_device_type_iphone() -> None:
    ua = (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15"
    )
    assert detect_device_type(ua) == "mobile"


def test_detect_device_type_chrome_desktop() -> None:
    ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    )
    assert detect_device_type(ua) == "desktop"


def test_detect_device_type_ipad() -> None:
    assert detect_device_type("Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X)") == "tablet"


def test_record_view_route() -> None:
    client = TestClient(create_app())
    with patch("api.routes.demo_tracking.get_demo_tracking_store") as mock_get:
        store = MagicMock()
        store.is_configured.return_value = True
        store.record_view = AsyncMock(
            return_value={
                "id": "view-1",
                "device_type": "mobile",
                "project_id": "proj-1",
            }
        )
        mock_get.return_value = store

        res = client.post(
            "/api/demo-tracking/view",
            json={
                "project_id": "proj-1",
                "demo_url": "https://demo.pages.dev/x",
            },
            headers={"User-Agent": "iPhone"},
        )

    assert res.status_code == 200
    assert res.json()["recorded"] is True
    store.record_view.assert_awaited_once()


def test_get_stats_route() -> None:
    client = TestClient(create_app())
    stats = {
        "total_views": 10,
        "unique_ips": 4,
        "by_device": {"mobile": 6, "tablet": 1, "desktop": 3},
        "last_viewed_at": "2026-06-16T10:00:00+00:00",
        "views_this_week": 5,
        "views_this_month": 8,
    }
    with patch("api.routes.demo_tracking.get_demo_tracking_store") as mock_get:
        store = MagicMock()
        store.is_configured.return_value = True
        store.get_stats = AsyncMock(return_value=stats)
        mock_get.return_value = store

        res = client.get("/api/demo-tracking/proj-1/stats")

    assert res.status_code == 200
    body = res.json()
    assert body["total_views"] == 10
    assert body["by_device"]["mobile"] == 6


def test_get_stats_aggregation() -> None:
    asyncio.run(_test_get_stats_aggregation())


async def _test_get_stats_aggregation() -> None:
    store = DemoTrackingStore()
    mock_supabase = MagicMock()
    mock_supabase.is_configured.return_value = True
    mock_supabase._rest_url.return_value = "https://example.supabase.co/rest/v1"
    mock_supabase._headers.return_value = {"apikey": "x"}
    store._supabase = mock_supabase

    rows = [
        {
            "visitor_ip": "1.1.1.1",
            "device_type": "mobile",
            "created_at": "2026-06-16T10:00:00+00:00",
        },
        {
            "visitor_ip": "1.1.1.1",
            "device_type": "desktop",
            "created_at": "2026-06-15T10:00:00+00:00",
        },
    ]
    mock_resp = MagicMock()
    mock_resp.json.return_value = rows

    with patch("db.demo_tracking_store.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client
        with patch("db.demo_tracking_store._raise_for_status"):
            stats = await store.get_stats("proj-1")

    assert stats["total_views"] == 2
    assert stats["unique_ips"] == 1
    assert stats["by_device"]["mobile"] == 1
    assert stats["by_device"]["desktop"] == 1

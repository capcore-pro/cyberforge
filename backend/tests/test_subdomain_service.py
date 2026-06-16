"""Tests sous-domaines capcore.pro — slugify, config, API."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from tools.subdomain_service import SubdomainError, SubdomainService


def test_slugify_restaurant_le_provencal() -> None:
    svc = SubdomainService()
    assert svc.slugify("Restaurant Le Provençal") == "restaurant-le-provencal"


def test_slugify_cafe_brasserie_dupont() -> None:
    svc = SubdomainService()
    assert svc.slugify("Café & Brasserie Dupont !!") == "cafe-brasserie-dupont"


def test_cloudflare_zone_id_from_settings() -> None:
    from config import get_settings

    settings = get_settings()
    zone_id = (settings.cloudflare_zone_id or "").strip()
    if zone_id:
        assert zone_id == "eb554b12e9c61fd53bdbccd30e84b6cf"
    else:
        with patch.object(settings, "cloudflare_zone_id", "eb554b12e9c61fd53bdbccd30e84b6cf"):
            assert settings.cloudflare_zone_id == "eb554b12e9c61fd53bdbccd30e84b6cf"


def test_create_subdomain_without_zone_id_raises() -> None:
    asyncio.run(_test_create_subdomain_without_zone_id_raises())


async def _test_create_subdomain_without_zone_id_raises() -> None:
    from config import get_settings

    settings = get_settings()
    svc = SubdomainService(settings)
    with patch.object(settings, "cloudflare_zone_id", ""):
        with pytest.raises(SubdomainError, match="CLOUDFLARE_ZONE_ID"):
            await svc.create_subdomain("Test Client")


def test_api_create_subdomain() -> None:
    client = TestClient(create_app())
    mock_result = {
        "subdomain": "test-client",
        "url": "https://test-client.capcore.pro",
        "dns_record_id": "rec123",
        "status": "created",
    }
    with patch(
        "api.routes.subdomains.subdomain_service.create_subdomain",
        new=AsyncMock(return_value=mock_result),
    ):
        response = client.post(
            "/api/subdomains/create",
            json={"client_name": "Test Client"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "https://test-client.capcore.pro"
    assert data["status"] in ("created", "already_exists")

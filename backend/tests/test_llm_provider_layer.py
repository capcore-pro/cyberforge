"""Tests LLM Provider Layer — migration, routing, fallback, agents."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import httpx
import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from db.supabase_store import get_supabase_store
from llm.base_provider import LLMRequest, LLMResponse
from llm.router import LLMRouter

VALID_BRIEF_JSON = """{
  "client_name": "Test Co",
  "project_type": "vitrine_next",
  "sector": "commerce",
  "description": "Description test suffisamment longue pour valider le brief.",
  "services": ["A", "B", "C"],
  "couleur_primaire": "#2563EB",
  "couleur_secondaire": "#F8FAFC",
  "font": "Inter",
  "ville": "Paris",
  "phone": "0102030405",
  "email": "test@example.com",
  "ambiance": "moderne",
  "mots_cles_seo": ["a", "b", "c"],
  "concurrents": [],
  "tendances": []
}"""


def _require_supabase() -> None:
    if not get_supabase_store().is_configured():
        pytest.skip("Supabase non configuré")


def test_llm_provider_tables_exist() -> None:
    asyncio.run(_test_llm_provider_tables_exist())


async def _test_llm_provider_tables_exist() -> None:
    _require_supabase()
    store = get_supabase_store()
    url = store._rest_url()
    headers = store._headers()
    async with httpx.AsyncClient(timeout=30.0) as client:
        for table in ("llm_providers", "llm_models"):
            resp = await client.get(f"{url}/{table}", headers=headers, params={"limit": "0"})
            assert resp.status_code == 200, f"Table {table} inaccessible"

        prov = await client.get(
            f"{url}/llm_providers",
            headers=headers,
            params={"slug": "in.(anthropic,openai,deepseek,ollama)"},
        )
        assert prov.status_code == 200
        slugs = {row["slug"] for row in prov.json()}
        assert slugs >= {"anthropic", "openai", "deepseek", "ollama"}


def test_llm_providers_api() -> None:
    _require_supabase()
    client = TestClient(create_app())
    resp = client.get("/api/llm/providers")
    assert resp.status_code == 200
    items = {row["slug"]: row for row in resp.json().get("items", [])}
    assert items["anthropic"]["available"] is True
    assert items["openai"]["available"] is True
    assert items["deepseek"]["available"] is True
    assert "ollama" in items
    assert isinstance(items["ollama"]["available"], bool)


def test_ollama_provider_availability_no_crash() -> None:
    asyncio.run(_test_ollama_provider_availability_no_crash())


async def _test_ollama_provider_availability_no_crash() -> None:
    from llm.providers.ollama_provider import OllamaProvider

    with patch("llm.providers.ollama_provider.get_settings") as mock_settings:
        mock_settings.return_value.ollama_base_url = None
        assert OllamaProvider().is_available() is False

    with patch("llm.providers.ollama_provider.get_settings") as mock_settings:
        mock_settings.return_value.ollama_base_url = "http://127.0.0.1:11434"
        with patch("httpx.Client") as client_cls:
            client_cls.return_value.__enter__.return_value.get.return_value.status_code = 200
            assert OllamaProvider().is_available() is True

    with patch("llm.providers.ollama_provider.get_settings") as mock_settings:
        mock_settings.return_value.ollama_base_url = "http://127.0.0.1:11434"
        with patch("httpx.Client") as client_cls:
            client_cls.return_value.__enter__.return_value.get.side_effect = OSError(
                "connection refused"
            )
            assert OllamaProvider().is_available() is False


def test_llm_router_primary_generation() -> None:
    asyncio.run(_test_llm_router_primary_generation())


async def _test_llm_router_primary_generation() -> None:
    router = LLMRouter()
    router._refresh_providers = lambda: None  # type: ignore[method-assign]
    mock_response = LLMResponse(
        content="<html><body>ok</body></html>",
        model="claude-sonnet-4-5",
        provider="anthropic",
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
    )
    anthropic_provider = MagicMock()
    anthropic_provider.provider_slug = "anthropic"
    anthropic_provider.is_available.return_value = True
    anthropic_provider.generate = AsyncMock(return_value=mock_response)
    router._providers = {"anthropic": anthropic_provider}

    result = await router.route(
        LLMRequest(messages=[{"role": "user", "content": "genere html"}]),
        task_type="generation",
    )
    assert result.provider == "anthropic"
    assert result.content.startswith("<html>")
    anthropic_provider.generate.assert_awaited_once()


def test_llm_router_fallback_with_audit() -> None:
    asyncio.run(_test_llm_router_fallback_with_audit())


async def _test_llm_router_fallback_with_audit() -> None:
    _require_supabase()
    router = LLMRouter()
    router._refresh_providers = lambda: None  # type: ignore[method-assign]
    anthropic_provider = MagicMock()
    anthropic_provider.provider_slug = "anthropic"
    anthropic_provider.is_available.return_value = True
    anthropic_provider.generate = AsyncMock(side_effect=RuntimeError("API down"))

    openai_provider = MagicMock()
    openai_provider.provider_slug = "openai"
    openai_provider.is_available.return_value = True
    openai_provider.generate = AsyncMock(
        return_value=LLMResponse(
            content="fallback ok",
            model="gpt-4o",
            provider="openai",
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
        )
    )
    router._providers = {
        "anthropic": anthropic_provider,
        "openai": openai_provider,
    }

    result = await router.route(
        LLMRequest(messages=[{"role": "user", "content": "hello"}]),
        task_type="generation",
    )
    assert result.provider == "openai"
    await asyncio.sleep(0.5)

    from db.audit_store import get_audit_store

    events = await get_audit_store().list_events(
        event_type="llm_provider_fallback",
        limit=10,
    )
    assert any(
        isinstance(e.get("event_data"), dict)
        and e["event_data"].get("task_type") == "generation"
        for e in events
    )


def test_brief_ai_fallback_on_anthropic_error() -> None:
    asyncio.run(_test_brief_ai_fallback_on_anthropic_error())


async def _test_brief_ai_fallback_on_anthropic_error() -> None:
    from agents.brief_ai import BriefAI

    fallback_response = LLMResponse(
        content=VALID_BRIEF_JSON,
        model="deepseek-chat",
        provider="deepseek",
        input_tokens=50,
        output_tokens=20,
        total_tokens=70,
    )

    async def _to_thread_raises(_fn):
        raise anthropic.APIError("down", request=MagicMock(), body=None)

    with (
        patch("agents.brief_ai.get_effective_llm_key", return_value="test-key"),
        patch("agents.brief_ai.anthropic.Anthropic") as anthropic_cls,
        patch("agents.brief_ai.asyncio.to_thread", side_effect=_to_thread_raises),
        patch("llm.router.llm_router.route", new_callable=AsyncMock) as mock_route,
    ):
        mock_route.return_value = fallback_response
        brief = await BriefAI().run(
            prompt="Boulangerie artisanale à Lyon avec services pain et viennoiseries.",
            project_type="vitrine_next",
        )

    assert brief.get("project_type") == "vitrine_next"
    assert brief.get("sector") == "commerce"
    assert brief.get("usage", {}).get("provider") == "deepseek"
    mock_route.assert_awaited_once()
    anthropic_cls.assert_called_once()

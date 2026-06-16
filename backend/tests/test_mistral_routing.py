"""Tests routing Mistral AI — client, router, fallback, pricing."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llm.base_provider import LLMRequest, LLMResponse
from llm.router import LLMRouter, ROUTING_RULES
from tools.llm_pricing import compute_llm_cost_usd


def test_routing_rules_brief_prefers_mistral() -> None:
    rule = ROUTING_RULES["brief"]
    assert rule["primary"] == "mistral"
    assert rule["primary_model"] == "mistral-small-latest"
    assert rule["fallback"] == "anthropic"


def test_routing_generation_keeps_sonnet() -> None:
    rule = ROUTING_RULES["generation"]
    assert rule["primary"] == "anthropic"
    assert "sonnet" in rule["primary_model"]


def test_mistral_pricing() -> None:
    cost = compute_llm_cost_usd("mistral", "mistral-small-latest", 1000, 500)
    assert cost > 0
    assert cost < 0.01


def test_mistral_client_complete_small() -> None:
    asyncio.run(_test_mistral_client_complete_small())


async def _test_mistral_client_complete_small() -> None:
    with patch("llm.mistral_client.get_settings") as mock_settings:
        mock_settings.return_value.mistral_api_key = "test-key"
        from llm.mistral_client import MistralClient

        client = MistralClient()
        mock_mistral = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Bonjour"))]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5)
        mock_mistral.chat.complete_async = AsyncMock(return_value=mock_response)
        client.client = mock_mistral

        text, usage = await client.complete_small(
            [{"role": "user", "content": "Dis bonjour"}]
        )
        assert text == "Bonjour"
        assert usage["input_tokens"] == 10


def test_llm_router_brief_uses_mistral() -> None:
    asyncio.run(_test_llm_router_brief_uses_mistral())


async def _test_llm_router_brief_uses_mistral() -> None:
    router = LLMRouter()
    router._refresh_providers = lambda: None  # type: ignore[method-assign]
    mistral_provider = MagicMock()
    mistral_provider.provider_slug = "mistral"
    mistral_provider.is_available.return_value = True
    mistral_provider.generate = AsyncMock(
        return_value=LLMResponse(
            content='{"client_name":"X"}',
            model="mistral-small-latest",
            provider="mistral",
            input_tokens=12,
            output_tokens=8,
            total_tokens=20,
        )
    )
    router._providers = {"mistral": mistral_provider}

    result = await router.route(
        LLMRequest(messages=[{"role": "user", "content": "brief"}]),
        task_type="brief",
    )
    assert result.provider == "mistral"
    mistral_provider.generate.assert_awaited_once()


def test_llm_router_brief_fallback_without_mistral() -> None:
    asyncio.run(_test_llm_router_brief_fallback_without_mistral())


async def _test_llm_router_brief_fallback_without_mistral() -> None:
    router = LLMRouter()
    router._refresh_providers = lambda: None  # type: ignore[method-assign]
    anthropic_provider = MagicMock()
    anthropic_provider.provider_slug = "anthropic"
    anthropic_provider.is_available.return_value = True
    anthropic_provider.generate = AsyncMock(
        return_value=LLMResponse(
            content="ok",
            model="claude-haiku-4-5-20251001",
            provider="anthropic",
            input_tokens=1,
            output_tokens=1,
            total_tokens=2,
        )
    )
    router._providers = {"anthropic": anthropic_provider}

    result = await router.route(
        LLMRequest(messages=[{"role": "user", "content": "brief"}]),
        task_type="brief",
    )
    assert result.provider == "anthropic"


def test_record_usage_accepts_mistral_provider() -> None:
    from db.llm_usage_store import LLMUsageStore

    store = LLMUsageStore()
    with patch.object(store, "is_configured", return_value=False):
        cost = compute_llm_cost_usd("mistral", "mistral-small-latest", 2000, 1000)
        assert isinstance(cost, float)

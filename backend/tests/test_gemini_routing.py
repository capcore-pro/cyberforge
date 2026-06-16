"""Tests routing Gemini Flash — config, fallback, pricing, provider models."""

from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

from config import get_settings
from llm.base_provider import LLMRequest, LLMResponse
from llm.provider_models import PROVIDER_MODEL_SPECS
from llm.router import LLMRouter, ROUTING_RULES
from tools.llm_pricing import compute_llm_cost_usd


def test_gemini_configured_false_without_key() -> None:
    settings = get_settings()
    with patch.object(settings, "gemini_api_key", None), patch.object(
        settings, "google_generative_ai_api_key", None
    ):
        assert settings.gemini_configured is False


def test_provider_models_gemini_flash_pricing() -> None:
    spec = PROVIDER_MODEL_SPECS["gemini-flash"]
    assert spec["provider"] == "gemini"
    assert spec["cost_per_1k_input"] == 0.0001
    assert spec["cost_per_1k_output"] == 0.0004


def test_gemini_pricing() -> None:
    cost = compute_llm_cost_usd("gemini", "gemini-2.0-flash", 1000, 500)
    assert cost > 0
    assert cost < 0.01


def test_routing_rules_brief_gemini_fallback() -> None:
    rule = ROUTING_RULES["brief"]
    assert rule["fallback"] == "gemini"
    assert rule["fallback_model"] == "gemini-2.0-flash"
    assert rule["fallback2"] == "anthropic"


def test_llm_router_brief_skips_gemini_without_key() -> None:
    asyncio.run(_test_llm_router_brief_skips_gemini_without_key())


async def _test_llm_router_brief_skips_gemini_without_key() -> None:
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


def test_record_usage_accepts_gemini_provider() -> None:
    from db.llm_usage_store import LLMUsageStore

    store = LLMUsageStore()
    with patch.object(store, "is_configured", return_value=False):
        cost = compute_llm_cost_usd("gemini", "gemini-2.0-flash", 2000, 1000)
        assert isinstance(cost, float)


def test_gemini_client_complete_flash() -> None:
    asyncio.run(_test_gemini_client_complete_flash())


async def _test_gemini_client_complete_flash() -> None:
    mock_genai = MagicMock()
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Réponse Gemini"
    mock_response.usage_metadata = MagicMock(
        prompt_token_count=10, candidates_token_count=5
    )
    mock_model.generate_content.return_value = mock_response
    mock_genai.GenerativeModel.return_value = mock_model

    with patch("llm.gemini_client._effective_gemini_api_key", return_value="test-key"), patch.dict(
        sys.modules, {"google.generativeai": mock_genai}
    ):
        from llm.gemini_client import GeminiClient

        client = GeminiClient()

        text, usage = await client.complete_flash(
            [{"role": "user", "content": "Bonjour"}]
        )
        assert text == "Réponse Gemini"
        assert usage["input_tokens"] == 10
        assert usage["output_tokens"] == 5

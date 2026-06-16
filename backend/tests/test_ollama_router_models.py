"""Tests modèles Ollama locaux — deepseek-r1 et phi4 dans le router."""

from __future__ import annotations

from llm.provider_models import PROVIDER_MODEL_SPECS
from llm.router import ROUTING_RULES, _routing_chain
from tools.llm_pricing import compute_llm_cost_usd


def test_provider_models_ollama_deepseek_r1_zero_cost() -> None:
    spec = PROVIDER_MODEL_SPECS["ollama-deepseek-r1"]
    assert spec["provider"] == "ollama"
    assert spec["model"] == "deepseek-r1"
    assert spec["cost_per_1k_input"] == 0.0
    assert spec["cost_per_1k_output"] == 0.0


def test_provider_models_ollama_phi4_zero_cost() -> None:
    spec = PROVIDER_MODEL_SPECS["ollama-phi4"]
    assert spec["provider"] == "ollama"
    assert spec["model"] == "phi4"
    assert spec["cost_per_1k_input"] == 0.0
    assert spec["cost_per_1k_output"] == 0.0


def test_ollama_pricing_is_free() -> None:
    cost = compute_llm_cost_usd("ollama", "deepseek-r1", 5000, 2000)
    assert cost == 0.0


def test_routing_brief_includes_ollama_local_models() -> None:
    chain = _routing_chain(ROUTING_RULES["brief"])
    ollama_models = [model for slug, model in chain if slug == "ollama"]
    assert ollama_models == ["deepseek-r1", "phi4", "qwen3"]


def test_routing_content_includes_ollama_local_models() -> None:
    chain = _routing_chain(ROUTING_RULES["content"])
    ollama_models = [model for slug, model in chain if slug == "ollama"]
    assert ollama_models == ["deepseek-r1", "phi4"]

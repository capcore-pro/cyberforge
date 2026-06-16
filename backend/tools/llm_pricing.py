"""
Tarification LLM (USD) — coût réel à partir des tokens API.
"""

from __future__ import annotations

from llm.provider_models import PROVIDER_MODEL_SPECS

# USD par million de tokens (input, output)
_MODEL_RATES: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-5": (3.0, 15.0),
    "claude-sonnet-4-20250514": (3.0, 15.0),
    "claude-haiku-4-5-20251001": (0.80, 4.0),
    "claude-3-5-haiku-20241022": (0.80, 4.0),
    "mistral-small-latest": (0.6, 1.8),
    "mistral-large-latest": (4.0, 12.0),
}

_DEFAULT_INPUT_PER_M = 3.0
_DEFAULT_OUTPUT_PER_M = 15.0


def _rates_for_model(provider: str, model: str) -> tuple[float, float]:
    key = (model or "").strip().lower()
    prov = (provider or "").strip().lower()

    if prov == "mistral":
        if "large" in key:
            spec = PROVIDER_MODEL_SPECS["mistral-large"]
        else:
            spec = PROVIDER_MODEL_SPECS["mistral-small"]
        return (
            float(spec["cost_per_1k_input"]) * 1000,
            float(spec["cost_per_1k_output"]) * 1000,
        )

    if prov == "gemini":
        spec = PROVIDER_MODEL_SPECS["gemini-flash"]
        return (
            float(spec["cost_per_1k_input"]) * 1000,
            float(spec["cost_per_1k_output"]) * 1000,
        )

    for name, rates in _MODEL_RATES.items():
        if name in key or key in name:
            return rates
    return _DEFAULT_INPUT_PER_M, _DEFAULT_OUTPUT_PER_M


def compute_llm_cost_usd(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Coût USD indicatif à partir des tokens réels."""
    inp = max(0, int(input_tokens or 0))
    out = max(0, int(output_tokens or 0))
    in_rate, out_rate = _rates_for_model(provider, model)
    cost = (inp / 1_000_000 * in_rate) + (out / 1_000_000 * out_rate)
    return round(cost, 6)

"""
Catalogue modèles LLM — coûts indicatifs (USD / 1k tokens).
Utilisé pour le pricing et le dashboard.
"""

from __future__ import annotations

PROVIDER_MODEL_SPECS: dict[str, dict[str, object]] = {
    "mistral-small": {
        "provider": "mistral",
        "model": "mistral-small-latest",
        "cost_per_1k_input": 0.0006,
        "cost_per_1k_output": 0.0018,
        "max_tokens": 32768,
        "supports_system": True,
    },
    "mistral-large": {
        "provider": "mistral",
        "model": "mistral-large-latest",
        "cost_per_1k_input": 0.004,
        "cost_per_1k_output": 0.012,
        "max_tokens": 131072,
        "supports_system": True,
    },
    "anthropic-haiku": {
        "provider": "anthropic",
        "model": "claude-haiku-4-5-20251001",
        "cost_per_1k_input": 0.0008,
        "cost_per_1k_output": 0.004,
        "max_tokens": 200000,
        "supports_system": True,
    },
    "anthropic-sonnet": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-5",
        "cost_per_1k_input": 0.003,
        "cost_per_1k_output": 0.015,
        "max_tokens": 200000,
        "supports_system": True,
    },
    "gemini-flash": {
        "provider": "gemini",
        "model": "gemini-2.0-flash",
        "cost_per_1k_input": 0.0001,
        "cost_per_1k_output": 0.0004,
        "max_tokens": 8192,
        "supports_system": True,
    },
}

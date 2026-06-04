"""
Estimation de coût des appels LLM (ordres de grandeur, USD).
Les tarifs réels varient selon le fournisseur — valeur indicative pour l'UI.
"""

# USD par million de tokens (moyenne entrée/sortie)
_COST_PER_MILLION: dict[tuple[str, str], float] = {
    ("deepseek", "deepseek-chat"): 0.21,
    ("gemini", "gemini-2.0-flash"): 0.15,
    ("gemini", "gemini-1.5-flash"): 0.15,
    ("anthropic", "claude-haiku-4-5-20251001"): 0.85,
    ("anthropic", "claude-sonnet-4-20250514"): 9.0,
}

_DEFAULT_PER_MILLION = 1.0


def estimate_cost_usd(
    provider: str,
    model: str,
    input_chars: int,
    output_chars: int,
) -> float:
    """Estime le coût en USD à partir du volume de texte (≈ 4 car./token)."""
    tokens = max(1, (input_chars + output_chars) // 4)
    rate = _COST_PER_MILLION.get((provider, model), _DEFAULT_PER_MILLION)
    return round(tokens / 1_000_000 * rate, 5)

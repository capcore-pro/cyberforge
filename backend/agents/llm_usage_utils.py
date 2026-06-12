"""Extraction et fusion des métriques usage Anthropic."""

from __future__ import annotations

from typing import Any


def usage_from_anthropic_response(
    response: Any,
    model: str,
    *,
    provider: str = "anthropic",
) -> dict[str, Any] | None:
    """Lit response.usage ; retourne None si absent."""
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
    if input_tokens <= 0 and output_tokens <= 0:
        return None
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "model": model,
        "provider": provider,
    }


def merge_usage(
    left: dict[str, Any] | None,
    right: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Fusionne deux blocs usage (ex. retries GeneratorAI / PaymentAI)."""
    if not left:
        return right
    if not right:
        return left
    inp = int(left.get("input_tokens") or 0) + int(right.get("input_tokens") or 0)
    out = int(left.get("output_tokens") or 0) + int(right.get("output_tokens") or 0)
    model = str(right.get("model") or left.get("model") or "")
    provider = str(right.get("provider") or left.get("provider") or "anthropic")
    return {
        "input_tokens": inp,
        "output_tokens": out,
        "total_tokens": inp + out,
        "model": model,
        "provider": provider,
    }


def pop_agent_usage(result: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Retire la clé usage d'un résultat agent avant persistance métier."""
    if not isinstance(result, dict):
        return {}, None
    payload = dict(result)
    usage = payload.pop("usage", None)
    if isinstance(usage, dict):
        return payload, usage
    return payload, None

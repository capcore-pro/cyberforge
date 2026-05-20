"""
Résolution des clés LLM — coffre chiffré (prioritaire) puis variables d'environnement.
"""

from __future__ import annotations

from pydantic import SecretStr

from config import Settings, plain_secret_str
from security.secret_vault import get_secret_vault

LLM_ENV_KEYS = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "DEEPSEEK_API_KEY",
    "GOOGLE_GENERATIVE_AI_API_KEY",
)

_SETTINGS_FIELD_BY_ENV: dict[str, str] = {
    "OPENAI_API_KEY": "openai_api_key",
    "ANTHROPIC_API_KEY": "anthropic_api_key",
    "DEEPSEEK_API_KEY": "deepseek_api_key",
    "GOOGLE_GENERATIVE_AI_API_KEY": "google_generative_ai_api_key",
}

LLM_KEYS_UNAVAILABLE_MSG = (
    "Aucune clé LLM disponible. Ouvrez Paramètres, déverrouillez le coffre "
    "et enregistrez au moins une clé (DeepSeek, Gemini ou Anthropic)."
)


def get_effective_llm_key(env_name: str, settings: Settings) -> str | None:
    """Clé depuis le coffre déverrouillé, sinon depuis l'environnement (.env)."""
    vault_value = get_secret_vault().peek(env_name)
    if vault_value:
        return vault_value

    field = _SETTINGS_FIELD_BY_ENV.get(env_name)
    if not field:
        return None
    raw = getattr(settings, field, None)
    if raw is None:
        return None
    if isinstance(raw, SecretStr):
        text = plain_secret_str(raw)
        return text or None
    text = str(raw).strip()
    return text or None


def any_llm_key_configured(settings: Settings) -> bool:
    """True si au moins un fournisseur LLM est configuré (coffre ou .env)."""
    if settings.ollama_base_url:
        return True
    return any(get_effective_llm_key(name, settings) for name in LLM_ENV_KEYS)


def llm_provider_flags(settings: Settings) -> dict[str, bool]:
    return {
        "openai": bool(get_effective_llm_key("OPENAI_API_KEY", settings)),
        "anthropic": bool(get_effective_llm_key("ANTHROPIC_API_KEY", settings)),
        "deepseek": bool(get_effective_llm_key("DEEPSEEK_API_KEY", settings)),
        "gemini": bool(
            get_effective_llm_key("GOOGLE_GENERATIVE_AI_API_KEY", settings)
        ),
    }

"""Tests statut agents pipeline v2 — prérequis clés coffre / .env / Settings."""

from pydantic import SecretStr

from config import Settings
from security.agent_readiness import agent_is_active, deploy_ready, supabase_ready


def _settings(**kwargs: object) -> Settings:
    return Settings(**kwargs)


def test_electron_always_active() -> None:
    assert agent_is_active("electron") is True


def test_brief_active_with_anthropic_env(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert agent_is_active("brief") is True
    assert agent_is_active("generator") is True
    assert agent_is_active("supervisor") is True


def test_brief_active_with_anthropic_settings(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    settings = _settings(anthropic_api_key=SecretStr("sk-ant-settings"))
    assert agent_is_active("brief", settings) is True


def test_brief_inactive_without_anthropic(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    settings = _settings(anthropic_api_key=None)
    assert agent_is_active("brief", settings) is False


def test_deploy_requires_pexels_and_cloudflare_account(monkeypatch) -> None:
    monkeypatch.setattr("security.agent_readiness._env_nonempty", lambda _name: False)
    monkeypatch.setattr("security.agent_readiness._vault_nonempty", lambda _name: False)

    missing_account = _settings(
        pexels_api_key=SecretStr("pexels-key"),
        cloudflare_api_token=SecretStr("cf-token"),
        cloudflare_account_id=None,
    )
    assert deploy_ready(missing_account) is False

    complete = _settings(
        pexels_api_key=SecretStr("pexels-key"),
        cloudflare_account_id=SecretStr("cf-account"),
        cloudflare_api_token=SecretStr("cf-token"),
    )
    assert deploy_ready(complete) is True


def test_deploy_active_from_settings_fields(monkeypatch) -> None:
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    settings = _settings(
        pexels_api_key=SecretStr("pexels-settings"),
        cloudflare_account_id=SecretStr("acct"),
        cloudflare_api_token=SecretStr("token"),
    )
    assert deploy_ready(settings) is True
    assert agent_is_active("deploy", settings) is True


def test_deploy_inactive_without_pexels(monkeypatch) -> None:
    monkeypatch.setattr("security.agent_readiness._env_nonempty", lambda _name: False)
    monkeypatch.setattr("security.agent_readiness._vault_nonempty", lambda _name: False)
    settings = _settings(
        pexels_api_key=None,
        cloudflare_account_id=SecretStr("cf-account"),
        cloudflare_api_token=SecretStr("cf-token"),
    )
    assert deploy_ready(settings) is False


def test_database_auth_require_supabase_url_and_secret() -> None:
    incomplete = _settings(
        supabase_url="https://example.supabase.co",
        supabase_secret_key=None,
    )
    assert supabase_ready(incomplete) is False

    settings = _settings(
        supabase_url="https://example.supabase.co",
        supabase_secret_key=SecretStr("service-role"),
    )
    assert supabase_ready(settings) is True
    assert agent_is_active("database", settings) is True
    assert agent_is_active("auth", settings) is True


def test_payment_requires_stripe(monkeypatch) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    assert agent_is_active("payment") is True

    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    settings = _settings(stripe_secret_key=SecretStr("sk_settings"))
    assert agent_is_active("payment", settings) is True

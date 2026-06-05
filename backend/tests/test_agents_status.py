"""Tests statut agents pipeline v2 — prérequis clés .env."""

import os

from api.routes.agents_status import _agent_is_active


def test_electron_always_active() -> None:
    assert _agent_is_active("electron") is True


def test_brief_active_with_anthropic(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert _agent_is_active("brief") is True
    assert _agent_is_active("generator") is True
    assert _agent_is_active("supervisor") is True


def test_brief_inactive_without_anthropic(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert _agent_is_active("brief") is False


def test_deploy_requires_pexels_and_cloudflare(monkeypatch) -> None:
    monkeypatch.setenv("PEXELS_API_KEY", "pexels-key")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "cf-token")
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
    assert _agent_is_active("deploy") is True


def test_deploy_inactive_without_pexels(monkeypatch) -> None:
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "cf-token")
    assert _agent_is_active("deploy") is False


def test_database_auth_require_supabase(monkeypatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    assert _agent_is_active("database") is True
    assert _agent_is_active("auth") is True


def test_payment_requires_stripe(monkeypatch) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    assert _agent_is_active("payment") is True

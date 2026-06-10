"""Tests GeneratorAI — injection auth_schema et routage app web."""

from __future__ import annotations

from agents.generator_ai import _build_user_message, _is_app_web_brief


def test_is_app_web_brief() -> None:
    assert _is_app_web_brief({"project_type": "application_web"})
    assert not _is_app_web_brief({"project_type": "vitrine_next"})


def test_auth_schema_injected_in_user_message() -> None:
    brief = {
        "client_name": "Test",
        "project_type": "application_web",
        "auth_schema": {
            "auth_type": "multi_user",
            "roles": ["admin", "manager", "employee"],
            "summary": "CRM multi-utilisateurs avec rôles.",
            "sql": "-- ignored in prompt",
        },
    }
    msg = _build_user_message(brief)
    assert "## auth_schema" in msg
    assert "Type : multi_user" in msg
    assert "Rôles : admin, manager, employee" in msg
    assert "CRM multi-utilisateurs" in msg


def test_auth_schema_absent_no_block() -> None:
    brief = {"client_name": "Test", "project_type": "application_web"}
    msg = _build_user_message(brief)
    assert "## auth_schema" not in msg

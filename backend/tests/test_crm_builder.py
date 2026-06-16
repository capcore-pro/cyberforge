"""Tests CRM Builder — routage prompt, pipeline AuthAI/DatabaseAI, mock BriefAI."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from agents.generator_ai import _build_system_prompt, _is_crm_brief
from agents.sector_generator_prompts import (
    CRM_APPENDIX,
    _brief_kind,
    build_sector_generator_appendix,
    is_crm_brief,
    resolve_sector_generator_profile,
)
from tools.export_cloudflare import deploy_uses_password_gate

CRM_MOCK_BRIEFS: dict[str, dict] = {
    "crm-clients": {
        "client_name": "CapCore CRM",
        "project_type": "crm",
        "sector": "CRM / clients",
        "description": "CRM interne pour gérer les prospects et clients CapCore",
        "couleur_primaire": "#0891b2",
        "prompt": (
            "TYPE: crm\n"
            "Client : CapCore CRM\n"
            "Secteur : CRM / clients\n"
            "Description : CRM interne pour gérer les prospects et clients CapCore"
        ),
        "database_schema": {
            "tables": [
                {
                    "name": "contacts",
                    "columns": [
                        {"name": "full_name", "type": "text"},
                        {"name": "email", "type": "text"},
                        {"name": "status", "type": "text"},
                    ],
                },
                {
                    "name": "deals",
                    "columns": [
                        {"name": "title", "type": "text"},
                        {"name": "amount", "type": "numeric"},
                        {"name": "stage", "type": "text"},
                    ],
                },
            ],
        },
        "auth_schema": {
            "auth_type": "multi_user",
            "roles": ["admin", "sales"],
            "summary": "CRM multi-utilisateurs",
        },
    },
    "crm-immobilier": {
        "client_name": "ImmoPro CRM",
        "project_type": "crm",
        "sector": "CRM / immobilier",
        "description": "CRM immobilier pour mandats, visites et compromis",
        "couleur_primaire": "#0f766e",
        "prompt": (
            "TYPE: crm\n"
            "Client : ImmoPro CRM\n"
            "Secteur : CRM / immobilier\n"
            "Description : CRM immobilier pour mandats, visites et compromis"
        ),
        "database_schema": {
            "tables": [
                {
                    "name": "acquereurs",
                    "columns": [
                        {"name": "nom", "type": "text"},
                        {"name": "budget", "type": "numeric"},
                    ],
                },
            ],
        },
        "auth_schema": {
            "auth_type": "multi_user",
            "roles": ["agent", "manager"],
            "summary": "Accès agents immobiliers",
        },
    },
}


def test_crm_brief_kind() -> None:
    brief = CRM_MOCK_BRIEFS["crm-clients"]
    assert _brief_kind(brief) == "crm"
    assert is_crm_brief(brief)
    assert _is_crm_brief(brief)
    assert not is_crm_brief({"project_type": "application_web"})


def test_crm_appendix_has_required_structure() -> None:
    assert 'id="login-screen"' in CRM_APPENDIX
    assert 'id="app-shell"' in CRM_APPENDIX
    assert 'id="view-pipeline"' in CRM_APPENDIX
    assert 'id="view-contacts"' in CRM_APPENDIX
    assert "demo2024" in CRM_APPENDIX
    assert "cursor:grab" in CRM_APPENDIX
    assert "#0f1117" in CRM_APPENDIX


def test_crm_clients_sector_profile_and_appendix() -> None:
    brief = CRM_MOCK_BRIEFS["crm-clients"]
    profile = resolve_sector_generator_profile(brief)
    assert profile is not None
    assert profile.id == "crm-clients"
    appendix = build_sector_generator_appendix(brief)
    assert "MODE CRM" in appendix
    assert "Pipeline Kanban" in appendix
    assert "Lead" in appendix or "Closing" in appendix


def test_crm_immobilier_sector_profile() -> None:
    brief = CRM_MOCK_BRIEFS["crm-immobilier"]
    profile = resolve_sector_generator_profile(brief)
    assert profile is not None
    assert profile.id == "crm-immobilier"
    appendix = build_sector_generator_appendix(brief)
    assert "Acquéreurs" in appendix or "Mandats" in appendix
    assert "Compromis" in appendix or "Acte" in appendix


def test_generator_system_prompt_routes_crm() -> None:
    for key in ("crm-clients", "crm-immobilier"):
        prompt = _build_system_prompt(CRM_MOCK_BRIEFS[key])
        assert "MODE CRM" in prompt
        assert 'id="view-pipeline"' in prompt
        assert "MODE APPLICATION WEB" not in prompt
        assert 'id="view-list"' not in prompt


def test_crm_project_type_is_password_gated() -> None:
    assert deploy_uses_password_gate("crm") is True


def test_pipeline_crm_runs_database_and_auth() -> None:
    asyncio.run(_test_pipeline_crm_runs_database_and_auth())


async def _test_pipeline_crm_runs_database_and_auth() -> None:
    from api.generation_stream import generation_event_store
    from pipeline import PipelineRequest, run_pipeline

    gid = "test-crm-pipeline"
    await generation_event_store.create(gid)

    minimal_html = "<!DOCTYPE html><html><body>" + ("z" * 5200) + "</body></html>"
    mock_brief = dict(CRM_MOCK_BRIEFS["crm-clients"])

    with (
        patch("pipeline.BriefAI") as brief_cls,
        patch("pipeline.GeneratorAI") as gen_cls,
        patch("pipeline.DeployAI") as dep_cls,
        patch("pipeline.SupervisorAI") as sup_cls,
        patch("agents.database_ai.run", new_callable=AsyncMock) as mock_db,
        patch("agents.auth_ai.run", new_callable=AsyncMock) as mock_auth,
        patch("agents.deploy_ai.deploy_html_demo", new_callable=AsyncMock) as mock_deploy,
        patch("agents.deploy_ai.inject_pexels_images", new_callable=AsyncMock) as mock_pexels,
    ):
        brief_cls.return_value.run = AsyncMock(return_value=mock_brief)
        mock_db.return_value = mock_brief["database_schema"]
        mock_auth.return_value = mock_brief["auth_schema"]
        gen_cls.return_value.run = AsyncMock(
            return_value={"success": True, "html": minimal_html}
        )
        mock_pexels.side_effect = lambda html, **_: html
        mock_deploy.return_value = (
            "https://demo.cyberforge.test/crm",
            "tok",
            "pass",
            "https://demo.cyberforge.test/unlock",
        )
        dep_cls.return_value.run = AsyncMock(
            return_value={
                "url": "https://demo.cyberforge.test/crm",
                "success": True,
                "html": minimal_html,
                "unlock_url": "https://demo.cyberforge.test/unlock",
                "demo_token": "tok",
                "demo_password": "pass",
            }
        )

        supervisor = sup_cls.return_value
        supervisor.validate_brief = AsyncMock(return_value={"valid": True, "errors": []})
        supervisor.validate_database = AsyncMock(
            return_value={"valid": True, "errors": []}
        )
        supervisor.validate_html = AsyncMock(return_value={"valid": True, "errors": []})
        supervisor.validate_deployment = AsyncMock(
            return_value={"valid": True, "errors": []}
        )

        result = await run_pipeline(
            PipelineRequest(
                prompt=mock_brief["prompt"],
                project_type="crm",
            ),
            generation_id=gid,
        )

    assert result["success"] is True
    mock_db.assert_awaited_once()
    mock_auth.assert_awaited_once()
    assert mock_db.await_args.kwargs.get("project_type") == "crm"
    assert mock_auth.await_args.kwargs.get("project_type") == "crm"

    session = generation_event_store.get_session(gid)
    assert session is not None
    log_messages = [
        e[2].get("message", "")
        for e in session.history
        if e[1] == "log"
    ]
    assert any("DatabaseAI" in m for m in log_messages)
    assert any("AuthAI" in m for m in log_messages)
    await generation_event_store.cleanup(gid)

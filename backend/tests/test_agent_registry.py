"""Tests Agent Registry — migration, API, status enrichi, audit."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from db.agent_registry_store import get_agent_registry_store
from db.audit_store import get_audit_store
from db.supabase_store import get_supabase_store

PIPELINE_AGENT_IDS = (
    "brief",
    "design_system",
    "supervisor",
    "generator",
    "deploy",
    "database",
    "auth",
    "payment",
)


def _require_supabase() -> None:
    if not get_supabase_store().is_configured():
        pytest.skip("Supabase non configuré")


def test_agents_table_seeded() -> None:
    asyncio.run(_test_agents_table_seeded())


async def _test_agents_table_seeded() -> None:
    _require_supabase()
    store = get_agent_registry_store()
    rows = await store.list_all()
    assert len(rows) == 11
    agent_ids = {row["agent_id"] for row in rows}
    assert "design_system" in agent_ids
    design = await store.get_by_agent_id("design_system")
    assert design is not None
    assert design["name"] == "DesignSystemAI"


def test_registry_api_list_all() -> None:
    _require_supabase()
    with TestClient(create_app()) as client:
        res = client.get("/api/agents/registry")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 11
    assert len(data["items"]) == 11
    generator = next(i for i in data["items"] if i["agent_id"] == "generator")
    assert generator["category"] == "generation"
    assert generator["model"] == "claude-sonnet-4-5"
    assert generator["provider"] == "anthropic"


def test_registry_pipeline_agents() -> None:
    _require_supabase()
    with TestClient(create_app()) as client:
        res = client.get("/api/agents/registry/pipeline")
    assert res.status_code == 200
    data = res.json()
    pipeline_ids = {item["agent_id"] for item in data["items"]}
    assert data["count"] == len(PIPELINE_AGENT_IDS)
    assert pipeline_ids == set(PIPELINE_AGENT_IDS)
    assert "email" not in pipeline_ids
    assert "media" not in pipeline_ids


def test_agents_status_enriched_from_registry() -> None:
    _require_supabase()
    with TestClient(create_app()) as client:
        res = client.get("/api/agents/status")
    assert res.status_code == 200
    data = res.json()
    assert data["total_agents"] == 11
    assert data["source"] == "registry"
    design = next(a for a in data["agents"] if a["id"] == "design_system")
    assert design["name"] == "DesignSystemAI"
    assert design["category"] == "design"
    generator = next(a for a in data["agents"] if a["id"] == "generator")
    assert generator["model"] == "claude-sonnet-4-5"
    assert generator["provider"] == "anthropic"
    assert isinstance(generator.get("capabilities"), list)


def test_agents_status_fallback_when_registry_unavailable() -> None:
    with patch(
        "api.routes.agents_status._load_registry_catalog",
        new=AsyncMock(return_value=None),
    ):
        with TestClient(create_app()) as client:
            res = client.get("/api/agents/status")
    assert res.status_code == 200
    data = res.json()
    assert data["source"] == "fallback"
    assert data["total_agents"] == 11
    assert any(a["id"] == "design_system" for a in data["agents"])


def test_update_model_and_audit() -> None:
    asyncio.run(_test_update_model_and_audit())


async def _test_update_model_and_audit() -> None:
    _require_supabase()
    store = get_agent_registry_store()
    audit = get_audit_store()
    original = await store.get_by_agent_id("generator")
    assert original is not None
    original_model = original.get("model")
    test_model = f"claude-sonnet-4-6-test-{uuid.uuid4().hex[:6]}"

    with TestClient(create_app()) as client:
        res = client.patch(
            "/api/agents/registry/generator/model",
            json={"model": test_model, "provider": "anthropic"},
        )
    assert res.status_code == 200
    assert res.json()["model"] == test_model

    updated = await store.get_by_agent_id("generator")
    assert updated is not None
    assert updated["model"] == test_model

    events = await audit.list_events(event_type="agent_model_updated", limit=20)
    match = next(
        (
            e
            for e in events
            if e.get("event_data", {}).get("agent_id") == "generator"
            and e.get("event_data", {}).get("model") == test_model
        ),
        None,
    )
    assert match is not None

    await store.update_model("generator", str(original_model or "claude-sonnet-4-5"), "anthropic")

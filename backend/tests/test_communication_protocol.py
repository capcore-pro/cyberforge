"""Tests Agent Communication Protocol Volume 04G."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from agents.message_bus import MESSAGE_TYPES, MessageBus
from api.generation_stream import generation_event_store
from api.main import create_app
from db.orchestration_store import get_orchestration_store
from db.supabase_store import get_supabase_store

COMM_TABLES = (
    "communication_channels",
    "message_acks",
    "communication_analytics",
)
SEED_CHANNELS = (
    "supervisor_corrections",
    "schema_propagation",
    "context_enrichment",
    "pipeline_events",
)


def _require_supabase() -> None:
    if not get_supabase_store().is_configured():
        pytest.skip("Supabase non configuré")


async def _wait_for_messages(
    session_id: str,
    *,
    message_type: str | None = None,
    attempts: int = 25,
) -> list[dict]:
    store = get_orchestration_store()
    for _ in range(attempts):
        messages = await store.get_messages(session_id)
        if message_type:
            matched = [m for m in messages if m.get("message_type") == message_type]
            if matched:
                return matched
        elif messages:
            return messages
        await asyncio.sleep(0.4)
    return await store.get_messages(session_id)


def test_communication_tables_and_channels() -> None:
    asyncio.run(_test_communication_tables_and_channels())


async def _test_communication_tables_and_channels() -> None:
    _require_supabase()
    store = get_supabase_store()
    url = store._rest_url()
    headers = store._headers()
    async with httpx.AsyncClient(timeout=30.0) as client:
        for table in COMM_TABLES:
            resp = await client.get(f"{url}/{table}", headers=headers, params={"limit": "0"})
            assert resp.status_code == 200, f"Table {table} inaccessible: {resp.status_code}"

    orch = get_orchestration_store()
    channels = await orch.list_channels()
    names = {c["channel_name"] for c in channels}
    assert names == set(SEED_CHANNELS)


def test_message_bus_handler_on_publish() -> None:
    asyncio.run(_test_message_bus_handler_on_publish())


async def _test_message_bus_handler_on_publish() -> None:
    received: list[dict] = []

    async def _handler(payload: dict) -> None:
        received.append(payload)

    mock_store = MagicMock()
    mock_store.send_message = AsyncMock(return_value={"id": "msg-1"})
    mock_store.increment_analytics = AsyncMock()

    bus = MessageBus(mock_store)
    bus.subscribe("correction_request", _handler)
    await bus._persist_and_notify(
        "sess-1",
        "supervisor_ai",
        "correction_request",
        {"errors": ["x"]},
        "generator_ai",
        "supervisor_corrections",
        "high",
    )

    mock_store.send_message.assert_awaited_once()
    assert received == [{"errors": ["x"]}]
    assert "correction_request" in MESSAGE_TYPES


def test_pipeline_publishes_correction_request_on_html_retry() -> None:
    asyncio.run(_test_pipeline_publishes_correction_request_on_html_retry())


async def _test_pipeline_publishes_correction_request_on_html_retry() -> None:
    _require_supabase()
    from pipeline import PipelineRequest, run_pipeline

    gid = f"test-comm-{uuid.uuid4().hex[:10]}"
    await generation_event_store.create(gid)
    minimal_html = "<!DOCTYPE html><html><body>" + ("x" * 3200) + "</body></html>"
    short_html = "<html><body>short</body></html>"
    validate_calls = {"n": 0}

    async def _validate_html(_html: str, _brief: dict) -> dict:
        validate_calls["n"] += 1
        if validate_calls["n"] == 1:
            return {
                "valid": False,
                "errors": ["HTML trop court"],
                "corrected_prompt": "allonger le HTML",
            }
        return {"valid": True, "errors": []}

    with (
        patch("pipeline.BriefAI") as brief_cls,
        patch("pipeline.GeneratorAI") as gen_cls,
        patch("pipeline.DeployAI") as dep_cls,
        patch("pipeline.SupervisorAI") as sup_cls,
        patch("agents.deploy_ai.deploy_html_demo", new_callable=AsyncMock) as mock_deploy,
        patch("agents.deploy_ai.inject_pexels_images", new_callable=AsyncMock) as mock_pexels,
    ):
        brief_cls.return_value.run = AsyncMock(
            return_value={
                "client_name": "Comm Test",
                "project_type": "vitrine_next",
                "description": "Test communication protocol.",
            }
        )
        gen_cls.return_value.run = AsyncMock(
            side_effect=[
                {"success": True, "html": short_html},
                {"success": True, "html": minimal_html},
            ]
        )
        mock_pexels.side_effect = lambda html, **_: html
        mock_deploy.return_value = (
            "https://demo.cyberforge.test/site",
            "tok",
            "pass",
            "https://demo.cyberforge.test/unlock",
        )
        dep_cls.return_value.run = AsyncMock(
            return_value={
                "url": "https://demo.cyberforge.test/site",
                "success": True,
                "html": minimal_html,
            }
        )
        supervisor = sup_cls.return_value
        supervisor.validate_brief = AsyncMock(return_value={"valid": True, "errors": []})
        supervisor.validate_design_system = MagicMock(side_effect=lambda ds, _b: ds)
        supervisor.validate_html = AsyncMock(side_effect=_validate_html)
        supervisor.validate_deployment = AsyncMock(return_value={"valid": True, "errors": []})

        result = await run_pipeline(
            PipelineRequest(prompt="Test communication.", project_type="vitrine_next"),
            generation_id=gid,
        )

    assert result["success"] is True
    session = await get_orchestration_store().get_session(gid)
    assert session is not None
    corrections = await _wait_for_messages(
        str(session["id"]),
        message_type="correction_request",
    )
    assert corrections
    assert corrections[0]["channel_name"] == "supervisor_corrections"
    assert corrections[0]["receiver_agent"] == "generator_ai"
    await generation_event_store.cleanup(gid)


def test_pipeline_publishes_schema_ready_for_ecommerce() -> None:
    asyncio.run(_test_pipeline_publishes_schema_ready_for_ecommerce())


async def _test_pipeline_publishes_schema_ready_for_ecommerce() -> None:
    _require_supabase()
    from pipeline import PipelineRequest, run_pipeline

    gid = f"test-schema-{uuid.uuid4().hex[:10]}"
    await generation_event_store.create(gid)
    minimal_html = "<!DOCTYPE html><html><body>" + ("x" * 3200) + "</body></html>"

    with (
        patch("pipeline.BriefAI") as brief_cls,
        patch("pipeline.GeneratorAI") as gen_cls,
        patch("pipeline.DeployAI") as dep_cls,
        patch("pipeline.SupervisorAI") as sup_cls,
        patch("agents.database_ai.run", new_callable=AsyncMock) as mock_db,
        patch("agents.payment_ai.run", new_callable=AsyncMock) as mock_pay,
        patch("agents.deploy_ai.deploy_html_demo", new_callable=AsyncMock) as mock_deploy,
        patch("agents.deploy_ai.inject_pexels_images", new_callable=AsyncMock) as mock_pexels,
    ):
        brief_cls.return_value.run = AsyncMock(
            return_value={
                "client_name": "Ecom Comm",
                "project_type": "ecommerce",
                "description": "Boutique ecommerce test communication.",
            }
        )
        mock_db.return_value = {"tables": [{"name": "products"}, {"name": "orders"}]}
        mock_pay.return_value = {"payment_type": "stripe"}
        gen_cls.return_value.run = AsyncMock(
            return_value={"success": True, "html": minimal_html}
        )
        mock_pexels.side_effect = lambda html, **_: html
        mock_deploy.return_value = (
            "https://demo.cyberforge.test/site",
            "tok",
            "pass",
            "https://demo.cyberforge.test/unlock",
        )
        dep_cls.return_value.run = AsyncMock(
            return_value={
                "url": "https://demo.cyberforge.test/site",
                "success": True,
                "html": minimal_html,
            }
        )
        supervisor = sup_cls.return_value
        supervisor.validate_brief = AsyncMock(return_value={"valid": True, "errors": []})
        supervisor.validate_design_system = MagicMock(side_effect=lambda ds, _b: ds)
        supervisor.validate_database = AsyncMock(return_value={"valid": True, "errors": []})
        supervisor.validate_payment = AsyncMock(return_value={"valid": True, "errors": []})
        supervisor.validate_html = AsyncMock(return_value={"valid": True, "errors": []})
        supervisor.validate_deployment = AsyncMock(return_value={"valid": True, "errors": []})

        result = await run_pipeline(
            PipelineRequest(prompt="Ecommerce comm test.", project_type="ecommerce"),
            generation_id=gid,
        )

    assert result["success"] is True
    session = await get_orchestration_store().get_session(gid)
    assert session is not None
    schema_msgs = await _wait_for_messages(
        str(session["id"]),
        message_type="schema_ready",
    )
    assert schema_msgs
    assert schema_msgs[0]["channel_name"] == "schema_propagation"
    await generation_event_store.cleanup(gid)


def test_communication_channels_api() -> None:
    _require_supabase()
    with TestClient(create_app()) as client:
        res = client.get("/api/communication/channels")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 4
    assert {item["channel_name"] for item in data["items"]} == set(SEED_CHANNELS)

"""Tests SSE génération v2 — store, pipeline events, sync, reconnexion."""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from api.generation_stream import generation_event_store


def _parse_sse_events(raw: str) -> list[tuple[int, str, dict[str, Any]]]:
    events: list[tuple[int, str, dict[str, Any]]] = []
    blocks = raw.split("\n\n")
    for block in blocks:
        if not block.strip():
            continue
        seq = 0
        event_type = ""
        data: dict[str, Any] = {}
        for line in block.splitlines():
            if line.startswith("id: "):
                seq = int(line[4:].strip())
            elif line.startswith("event: "):
                event_type = line[7:].strip()
            elif line.startswith("data: "):
                data = json.loads(line[6:])
        if event_type:
            events.append((seq, event_type, data))
    return events


def test_event_store_replay_without_duplicates() -> None:
    asyncio.run(_test_event_store_replay_without_duplicates())


async def _test_event_store_replay_without_duplicates() -> None:
    gid = "test-replay-001"
    await generation_event_store.create(gid)
    await generation_event_store.emit(gid, "agent_start", {"agent": "BriefAI", "step": 1, "total": 4})
    await generation_event_store.emit(gid, "agent_done", {"agent": "BriefAI", "step": 1, "duration_ms": 10})
    await generation_event_store.emit(gid, "done", {"url": "https://x.test", "html": "<html></html>", "duration_ms": 99})

    first: list[tuple[int, str, dict[str, Any]]] = []
    async for seq, etype, data in generation_event_store.iter_events(gid, after_seq=0):
        first.append((seq, etype, data))

    second: list[tuple[int, str, dict[str, Any]]] = []
    async for seq, etype, data in generation_event_store.iter_events(gid, after_seq=2):
        second.append((seq, etype, data))

    assert [e[1] for e in first] == ["agent_start", "agent_done", "done"]
    assert [e[1] for e in second] == ["done"]
    assert len(second) == 1
    await generation_event_store.cleanup(gid)


def test_pipeline_emits_four_agents_in_order() -> None:
    asyncio.run(_test_pipeline_emits_four_agents_in_order())


async def _test_pipeline_emits_four_agents_in_order() -> None:
    from pipeline import run_pipeline, PipelineRequest

    gid = "test-pipeline-order"
    await generation_event_store.create(gid)

    minimal_html = "<!DOCTYPE html><html><body>" + ("x" * 3200) + "</body></html>"

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
                "client_name": "Test",
                "project_type": "vitrine_next",
                "description": "Test vitrine",
            }
        )
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
                "unlock_url": "https://demo.cyberforge.test/unlock",
                "demo_token": "tok",
                "demo_password": "pass",
            }
        )

        supervisor = sup_cls.return_value
        supervisor.validate_brief = AsyncMock(return_value={"valid": True, "errors": []})
        supervisor.validate_html = AsyncMock(return_value={"valid": True, "errors": []})
        supervisor.validate_deployment = AsyncMock(return_value={"valid": True, "errors": []})

        result = await run_pipeline(
            PipelineRequest(prompt="Client Test — vitrine professionnelle.", project_type="vitrine_next"),
            generation_id=gid,
        )

    session = generation_event_store.get_session(gid)
    assert session is not None
    types = [e[1] for e in session.history]
    assert types.count("agent_start") == 4
    assert types.count("agent_done") == 4
    assert "done" in types
    assert result["success"] is True
    await generation_event_store.cleanup(gid)


def test_pipeline_emits_agent_retry_on_short_html() -> None:
    asyncio.run(_test_pipeline_emits_agent_retry_on_short_html())


async def _test_pipeline_emits_agent_retry_on_short_html() -> None:
    from pipeline import run_pipeline, PipelineRequest

    gid = "test-pipeline-retry"
    await generation_event_store.create(gid)

    short_html = "<html><body>court</body></html>"
    long_html = "<!DOCTYPE html><html><body>" + ("y" * 3200) + "</body></html>"
    calls = {"n": 0}

    async def _validate_html(_html: str, _brief: dict) -> dict[str, Any]:
        calls["n"] += 1
        if calls["n"] == 1:
            return {"valid": False, "errors": ["HTML trop court"], "corrected_prompt": "allonger"}
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
                "client_name": "Test",
                "project_type": "vitrine_next",
                "description": "Test",
            }
        )
        gen_cls.return_value.run = AsyncMock(
            side_effect=[
                {"success": True, "html": short_html},
                {"success": True, "html": long_html},
            ]
        )
        mock_pexels.side_effect = lambda html, **_: html
        mock_deploy.return_value = ("https://demo.test", "t", "p", "https://demo.test/u")
        dep_cls.return_value.run = AsyncMock(
            return_value={
                "url": "https://demo.test",
                "success": True,
                "html": long_html,
            }
        )
        supervisor = sup_cls.return_value
        supervisor.validate_brief = AsyncMock(return_value={"valid": True, "errors": []})
        supervisor.validate_html = AsyncMock(side_effect=_validate_html)
        supervisor.validate_deployment = AsyncMock(return_value={"valid": True, "errors": []})

        await run_pipeline(
            PipelineRequest(prompt="Client Test — vitrine.", project_type="vitrine_next"),
            generation_id=gid,
        )

    session = generation_event_store.get_session(gid)
    assert session is not None
    retries = [e for e in session.history if e[1] == "agent_retry"]
    assert len(retries) == 1
    assert retries[0][2]["reason"] == "HTML trop court"
    await generation_event_store.cleanup(gid)


def test_generate_sync_returns_full_json() -> None:
    from fastapi.testclient import TestClient

    from main import app

    minimal_html = "<!DOCTYPE html><html><body>" + ("z" * 3200) + "</body></html>"

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
                "client_name": "Sync",
                "project_type": "vitrine_next",
                "description": "Sync test",
            }
        )
        gen_cls.return_value.run = AsyncMock(
            return_value={"success": True, "html": minimal_html}
        )
        mock_pexels.side_effect = lambda html, **_: html
        mock_deploy.return_value = ("https://sync.test", "t", "p", "https://sync.test/u")
        dep_cls.return_value.run = AsyncMock(
            return_value={
                "url": "https://sync.test",
                "success": True,
                "html": minimal_html,
            }
        )
        supervisor = sup_cls.return_value
        supervisor.validate_brief = AsyncMock(return_value={"valid": True, "errors": []})
        supervisor.validate_html = AsyncMock(return_value={"valid": True, "errors": []})
        supervisor.validate_deployment = AsyncMock(return_value={"valid": True, "errors": []})

        tc = TestClient(app)
        resp = tc.post(
            "/api/generate/sync",
            json={"prompt": "Client Sync — vitrine test.", "project_type": "vitrine_next"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "https://sync.test" in body["url"]
    assert len(body["html"]) > 3000


def test_generate_async_start_returns_generation_id() -> None:
    from fastapi.testclient import TestClient

    from main import app

    async def _noop_pipeline(request, *, generation_id=None):
        await generation_event_store.emit(generation_id, "done", {"url": "", "html": "<html></html>", "duration_ms": 1})
        return {"success": True, "url": "", "html": "<html></html>"}

    with patch("api.routes.generate.run_pipeline", side_effect=_noop_pipeline):
        tc = TestClient(app)
        start = tc.post(
            "/api/generate",
            json={"prompt": "Client Stream — vitrine.", "project_type": "vitrine_next"},
        )
    assert start.status_code == 200
    body = start.json()
    assert body["status"] == "started"
    assert body["generation_id"]


def test_generate_sse_stream_and_reconnect() -> None:
    minimal_html = "<!DOCTYPE html><html><body>" + ("w" * 3200) + "</body></html>"
    gid = str(uuid4())

    async def _seed_events() -> None:
        await generation_event_store.create(gid)
        assert generation_event_store.exists(gid)
        await generation_event_store.emit(
            gid,
            "agent_start",
            {"agent": "BriefAI", "step": 1, "total": 4},
        )
        await generation_event_store.emit(
            gid,
            "agent_done",
            {"agent": "BriefAI", "step": 1, "duration_ms": 5},
        )
        for agent, step in (
            ("GeneratorAI", 2),
            ("SupervisorAI", 3),
            ("DeployAI", 4),
        ):
            await generation_event_store.emit(
                gid,
                "agent_start",
                {"agent": agent, "step": step, "total": 4},
            )
            await generation_event_store.emit(
                gid,
                "agent_done",
                {"agent": agent, "step": step, "duration_ms": 7},
            )
        await generation_event_store.emit(
            gid,
            "done",
            {
                "url": "https://stream.test",
                "html": minimal_html,
                "duration_ms": 42,
            },
        )

    asyncio.run(_seed_events())
    assert generation_event_store.exists(gid)

    from fastapi.testclient import TestClient

    from main import app

    tc = TestClient(app)
    response = tc.get(f"/api/generate/stream/{gid}")
    assert response.status_code == 200
    raw = response.text

    events = _parse_sse_events(raw)
    types = [e[1] for e in events]
    assert types.count("agent_start") == 4
    assert types.count("agent_done") == 4
    assert types[-1] == "done"
    assert events[-1][2]["url"] == "https://stream.test"

    response2 = tc.get(
        f"/api/generate/stream/{gid}",
        headers={"Last-Event-ID": "2"},
    )
    assert response2.status_code == 200
    raw2 = response2.text
    events2 = _parse_sse_events(raw2)
    assert all(seq > 2 for seq, _, _ in events2)
    assert events2[-1][1] == "done"  # tuple (seq, type, data)
    asyncio.run(generation_event_store.cleanup(gid))

"""Tests Volume 04D — Prompt Library complète."""

from __future__ import annotations

import asyncio
import subprocess
import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from db.prompt_store import get_prompt_store
from db.supabase_store import get_supabase_store

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_SCRIPT = REPO_ROOT / "backend" / "scripts" / "seed_prompts.py"

GENERATOR_APPENDIX_SLUGS = (
    "ecommerce-appendix",
    "app-web-appendix",
    "crm-appendix",
    "site-reservation-appendix",
)


def _require_supabase() -> None:
    if not get_supabase_store().is_configured():
        pytest.skip("Supabase non configuré")


def test_prompt_benchmarks_table_exists() -> None:
    asyncio.run(_test_prompt_benchmarks_table_exists())


async def _test_prompt_benchmarks_table_exists() -> None:
    _require_supabase()
    store = get_supabase_store()
    url = store._rest_url()
    headers = store._headers()
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{url}/prompt_benchmarks",
            headers=headers,
            params={"limit": "0"},
        )
        assert resp.status_code == 200


def test_prompt_versioning_and_rollback() -> None:
    asyncio.run(_test_prompt_versioning_and_rollback())


async def _test_prompt_versioning_and_rollback() -> None:
    _require_supabase()
    slug = f"version-test-{uuid.uuid4().hex[:8]}"
    app = create_app()
    client = TestClient(app)

    create_resp = client.post(
        "/api/prompts-library",
        json={
            "name": "Version Test",
            "slug": slug,
            "content": "contenu v1",
            "category_slug": "system",
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    prompt_id = create_resp.json()["id"]
    version_v1 = create_resp.json().get("version", "1.0.0")

    patch_resp = client.patch(
        f"/api/prompts-library/{prompt_id}",
        json={"content": "contenu v2", "changelog": "update test"},
    )
    assert patch_resp.status_code == 200, patch_resp.text
    assert patch_resp.json().get("content") == "contenu v2"

    versions_resp = client.get(f"/api/prompts-library/{prompt_id}/versions")
    assert versions_resp.status_code == 200
    versions = versions_resp.json().get("items", [])
    assert len(versions) >= 1

    rollback_resp = client.post(
        f"/api/prompts-library/{prompt_id}/rollback",
        json={"version": version_v1},
    )
    assert rollback_resp.status_code == 200, rollback_resp.text
    assert "contenu v1" in rollback_resp.json().get("content", "")


def test_prompt_benchmark_updates_quality_score() -> None:
    asyncio.run(_test_prompt_benchmark_updates_quality_score())


async def _test_prompt_benchmark_updates_quality_score() -> None:
    _require_supabase()
    slug = f"bench-test-{uuid.uuid4().hex[:8]}"
    app = create_app()
    client = TestClient(app)

    create_resp = client.post(
        "/api/prompts-library",
        json={
            "name": "Bench Test",
            "slug": slug,
            "content": "benchmark prompt",
            "category_slug": "system",
            "agent_slug": "generator_ai",
        },
    )
    assert create_resp.status_code == 200
    prompt_id = create_resp.json()["id"]

    bench_resp = client.post(
        f"/api/prompts-library/{prompt_id}/benchmark",
        json={
            "task_type": "generation",
            "quality_score": 85,
            "model_used": "claude-sonnet-4-5",
            "provider": "anthropic",
            "input_tokens": 2500,
            "output_tokens": 8000,
            "duration_ms": 8300,
            "cost_usd": 0.000127,
        },
    )
    assert bench_resp.status_code == 200, bench_resp.text
    assert bench_resp.json().get("quality_score") == 85

    prompt = await get_prompt_store().get_by_id(prompt_id)
    assert prompt is not None
    assert int(prompt.get("quality_score") or 0) == 85


def test_seed_prompts_seven_entries() -> None:
    _require_supabase()
    proc = subprocess.run(
        [sys.executable, str(SEED_SCRIPT)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout

    async def _check() -> None:
        store = get_prompt_store()
        for slug in (
            "brief-ai-system",
            "generator-ai-system",
            "supervisor-validation-rules",
            *GENERATOR_APPENDIX_SLUGS,
        ):
            row = await store.get_by_slug_any_status(slug)
            assert row is not None, f"Prompt seed manquant: {slug}"

        app = create_app()
        client = TestClient(app)
        resp = client.get("/api/prompts-library", params={"agent": "generator_ai"})
        assert resp.status_code == 200
        slugs = {p.get("slug") for p in resp.json().get("items", [])}
        for expected in GENERATOR_APPENDIX_SLUGS:
            assert expected in slugs

    asyncio.run(_check())


def test_generator_runtime_appendix_from_library() -> None:
    asyncio.run(_test_generator_runtime_appendix_from_library())


async def _test_generator_runtime_appendix_from_library() -> None:
    from agents.generator_ai import _get_mode_appendix

    brief = {"project_type": "ecommerce", "sector": "mode"}
    mock_store = MagicMock()
    mock_store.is_configured.return_value = True
    mock_store.get_by_slug = AsyncMock(
        return_value={"id": "prompt-eco-1", "content": "ECOMMERCE FROM DB"}
    )
    mock_store.increment_usage = AsyncMock()

    with patch("db.prompt_store.get_prompt_store", return_value=mock_store):
        content = await _get_mode_appendix(brief, "HARDCODED")

    assert content == "ECOMMERCE FROM DB"
    mock_store.increment_usage.assert_awaited_once_with("prompt-eco-1")

    mock_store.is_configured.return_value = False
    with patch("db.prompt_store.get_prompt_store", return_value=mock_store):
        fallback = await _get_mode_appendix(brief, "HARDCODED")
    assert fallback == "HARDCODED"

"""Tests Supervisor System Volume 04B — scoring, retries, planning, API."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from agents.planning_engine import PlanningEngine
from agents.quality_scorer import QualityScorer
from api.generation_stream import generation_event_store
from api.main import create_app
from db.supabase_store import get_supabase_store
from pipeline import MaxRetriesExceeded, _run_supervised

SUPERVISOR_TABLES = (
    "supervisor_decisions",
    "quality_reviews",
    "supervisor_metrics",
)


def _require_supabase() -> None:
    if not get_supabase_store().is_configured():
        pytest.skip("Supabase non configuré")


def _ecommerce_html() -> str:
    client = "Boutique Mode Paris"
    return f"""<!DOCTYPE html>
<html><head><title>{client}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter" rel="stylesheet">
<style>:root {{ --color-primary: #d4a843; }}</style>
</head><body>
<header><nav>Menu</nav></header>
<section class="hero" style="min-height:60vh"><h1>{client}</h1></section>
<section id="s1"><h2>Produits</h2></section>
<section id="s2"><h2>Services</h2></section>
<section id="s3"><h2>Contact</h2>
<img class="pexels-inject" src="#" alt="fashion">
</section>
<footer class="footer">© {client}</footer>
<script>
function addToCart() {{ stripe.checkout(); }}
const cart = [];
</script>
</body></html>"""


def test_supervisor_tables_exist() -> None:
    asyncio.run(_test_supervisor_tables_exist())


async def _test_supervisor_tables_exist() -> None:
    _require_supabase()
    store = get_supabase_store()
    url = store._rest_url()
    headers = store._headers()
    async with httpx.AsyncClient(timeout=30.0) as client:
        for table in SUPERVISOR_TABLES:
            resp = await client.get(f"{url}/{table}", headers=headers, params={"limit": "0"})
            assert resp.status_code == 200, f"Table {table} inaccessible: {resp.status_code}"


def test_quality_scorer_html_ecommerce() -> None:
    html = _ecommerce_html()
    brief = {
        "client_name": "Boutique Mode Paris",
        "project_type": "ecommerce",
        "couleur_primaire": "#d4a843",
    }
    score = QualityScorer.score_html(html, brief)
    assert 60 <= score <= 100


def test_max_retries_on_supervised_validation() -> None:
    asyncio.run(_test_max_retries_on_supervised_validation())


async def _test_max_retries_on_supervised_validation() -> None:
    async def _always_fail(_prompt: str) -> dict:
        return {"ok": False}

    async def _validate(_result: dict) -> dict:
        return {"valid": False, "errors": ["forced failure"], "warnings": []}

    with patch("pipeline._schedule_supervisor_decision"):
        with pytest.raises(MaxRetriesExceeded):
            await _run_supervised(
                "BriefAI",
                _always_fail,
                _validate,
                initial_prompt="test",
                generation_id="test-max-retries",
            )


def test_max_html_retries() -> None:
    asyncio.run(_test_max_html_retries())


async def _test_max_html_retries() -> None:
    from pipeline import MAX_HTML_RETRIES, PipelineRequest, _run_pipeline_body

    gid = f"test-html-retries-{uuid.uuid4().hex[:8]}"
    await generation_event_store.create(gid)
    minimal_html = "<html><body>short</body></html>"

    with (
        patch("pipeline.BriefAI") as brief_cls,
        patch("pipeline.GeneratorAI") as gen_cls,
        patch("pipeline.DeployAI") as dep_cls,
        patch("pipeline.SupervisorAI") as sup_cls,
        patch("pipeline._schedule_supervisor_decision"),
        patch("pipeline._schedule_quality_review"),
    ):
        brief_cls.return_value.run = AsyncMock(
            return_value={
                "client_name": "Retry Test",
                "project_type": "vitrine_next",
                "description": "Description suffisamment longue pour le test de validation HTML retry.",
                "services": ["A", "B", "C", "D"],
                "couleur_primaire": "#112233",
                "couleur_secondaire": "#445566",
                "sector": "test",
                "ambiance": "pro",
                "ville": "Paris",
                "email": "a@b.com",
                "phone": "0102030405",
                "mots_cles_seo": ["test"],
            }
        )
        gen_cls.return_value.run = AsyncMock(
            return_value={"success": True, "html": minimal_html}
        )
        dep_cls.return_value.run = AsyncMock(return_value={"success": True, "url": "https://x.pages.dev"})

        supervisor = sup_cls.return_value
        supervisor.validate_brief = AsyncMock(return_value={"valid": True, "errors": []})
        supervisor.validate_design_system = MagicMock(side_effect=lambda ds, _b: ds)
        supervisor.validate_html = AsyncMock(
            return_value={"valid": False, "errors": ["HTML trop court"], "warnings": []}
        )

        with pytest.raises(MaxRetriesExceeded):
            await _run_pipeline_body(
                PipelineRequest(prompt="Test retry html", project_type="vitrine_next"),
                generation_id=gid,
                pipeline_t0=0.0,
            )

    await generation_event_store.cleanup(gid)
    assert MAX_HTML_RETRIES == 3


def test_planning_engine_ecommerce() -> None:
    plan = PlanningEngine().build_plan(
        {
            "project_type": "ecommerce",
            "description": (
                "Boutique mode parisienne proposant vêtements tendance, accessoires "
                "et chaussures avec livraison rapide en France métropolitaine."
            ),
            "couleur_primaire": "#d4a843",
            "services": ["Robes", "Sacs", "Chaussures", "Accessoires"],
        }
    )
    assert "payment" in plan["agents"]
    assert plan["estimated_cost_usd"] > 0
    assert plan["risk_level"] == "low"
    assert plan["workflow_id"] == "ecommerce"


def test_supervisor_plan_api() -> None:
    with TestClient(create_app()) as client:
        res = client.post(
            "/api/supervisor/plan",
            json={
                "brief": {
                    "project_type": "vitrine_next",
                    "description": "Site vitrine pour boulangerie artisanale à Lyon.",
                    "couleur_primaire": "#c8a45a",
                }
            },
        )
    assert res.status_code == 200
    data = res.json()
    assert data["workflow_id"] == "vitrine_simple"
    assert "generator" in data["agents"]
    assert data["estimated_cost_usd"] > 0
    assert data["risk_level"] in ("low", "medium", "high")

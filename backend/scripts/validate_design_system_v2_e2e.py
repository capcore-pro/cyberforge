#!/usr/bin/env python3
"""
Validation E2E DesignSystemAI V2 — 3 scénarios mock (sans LLM).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from agents.design_system_ai import (
    build_design_system,
    format_design_system_for_prompt,
    inject_design_system_into_html,
)
from agents.deploy_ai import DeployAI
from api.generation_stream import TRACKED_TOTAL, generation_event_store
from pipeline import PipelineRequest, run_pipeline

SCENARIOS: tuple[dict[str, Any], ...] = (
    {
        "name": "vitrine_boulangerie",
        "brief": {
            "client_name": "Aux Délices",
            "project_type": "vitrine_next",
            "sector": "boulangerie",
            "couleur_primaire": "#5C3A21",
            "couleur_secondaire": "#FCF7F0",
            "description": "Boulangerie artisanale à Rouen, pains au levain et viennoiseries.",
            "services": ["Pain au levain", "Viennoiseries", "Pâtisseries"],
            "ambiance": "chaleureux",
            "ville": "Rouen",
            "phone": "02 00 00 00 00",
            "email": "contact@auxdelices.fr",
        },
        "expected_family": "premium_light",
    },
    {
        "name": "ecommerce_mode",
        "brief": {
            "client_name": "Maison Éclat",
            "project_type": "ecommerce",
            "sector": "mode",
            "couleur_primaire": "#d4a843",
            "couleur_secondaire": "#1a1a2e",
            "description": "Boutique mode en ligne, prêt-à-porter et accessoires tendance.",
            "services": ["Robes", "Sacs", "Bijoux"],
            "ambiance": "élégant",
            "ville": "Paris",
            "phone": "01 00 00 00 00",
            "email": "shop@maisoneclat.fr",
        },
        "expected_family": "premium_commerce",
    },
    {
        "name": "app_web_dashboard",
        "brief": {
            "client_name": "DataPulse",
            "project_type": "application_web",
            "sector": "dashboard-analytics",
            "couleur_primaire": "#6366f1",
            "couleur_secondaire": "#1e2535",
            "description": "Application web de tableau de bord analytics pour équipes produit.",
            "services": ["KPIs", "Rapports", "Alertes"],
            "ambiance": "professionnel",
            "ville": "Lyon",
            "phone": "04 00 00 00 00",
            "email": "hello@datapulse.fr",
        },
        "expected_family": "premium_dark",
    },
)


def _minimal_html(client: str) -> str:
    return (
        f"<!DOCTYPE html><html><head><title>{client}</title>"
        f"<style>body{{margin:0}}</style></head><body>"
        f"<header><nav>{client}</nav></header>"
        f"<section class='hero' style='min-height:100vh'>{client}</section>"
        f"<section>s1</section><section>s2</section><section>s3</section>"
        f"<img class='pexels-inject' alt='a'><img class='pexels-inject' alt='b'>"
        f"<img class='pexels-inject' alt='c'>"
        f"<footer><p>© {client}</p></footer></body></html>"
    )


def _check_design_system(brief: dict, expected_family: str) -> list[str]:
    errors: list[str] = []
    ds = build_design_system(brief)
    if ds.get("style_family") != expected_family:
        errors.append(f"style_family={ds.get('style_family')} != {expected_family}")
    css = ds.get("css_variables") or ""
    if ":root" not in css or "--color-primary" not in css:
        errors.append("css_variables invalide")
    prompt_block = format_design_system_for_prompt(ds)
    if "## design_system" not in prompt_block or not prompt_block.strip():
        errors.append("format_design_system_for_prompt vide")
    return errors


async def _check_pipeline_sse(brief: dict, client: str) -> list[str]:
    errors: list[str] = []
    gid = f"ds-e2e-{brief['project_type']}"
    await generation_event_store.create(gid)
    html = _minimal_html(client)

    with (
        patch("pipeline.BriefAI") as brief_cls,
        patch("pipeline.GeneratorAI") as gen_cls,
        patch("pipeline.DeployAI") as dep_cls,
        patch("agents.deploy_ai.deploy_html_demo", new_callable=AsyncMock) as mock_deploy,
        patch("agents.deploy_ai.inject_pexels_images", new_callable=AsyncMock) as mock_pexels,
        patch("agents.database_ai.run", new_callable=AsyncMock) as mock_db,
        patch("agents.auth_ai.run", new_callable=AsyncMock) as mock_auth,
        patch("agents.payment_ai.run", new_callable=AsyncMock) as mock_payment,
    ):
        mock_db.return_value = {"tables": [{"name": "users"}, {"name": "logs"}], "sql": "CREATE TABLE users;"}
        mock_auth.return_value = {
            "auth_type": "email_password",
            "roles": ["admin", "user"],
            "summary": "Auth mock",
        }
        mock_payment.return_value = {
            "payment_type": "stripe",
            "summary": "Paiement mock",
        }
        brief_cls.return_value.run = AsyncMock(return_value=dict(brief))
        gen_cls.return_value.run = AsyncMock(return_value={"success": True, "html": html})
        mock_pexels.side_effect = lambda h, **_: h
        mock_deploy.return_value = ("https://ds.test", "t", "p", "https://ds.test/u")

        real_deploy = DeployAI()

        async def _deploy_run(*args, **kwargs):
            return await real_deploy.run(*args, **kwargs)

        dep_cls.return_value.run = AsyncMock(side_effect=_deploy_run)

        from pipeline import SupervisorAI

        with (
            patch.object(SupervisorAI, "validate_brief", new_callable=AsyncMock) as vb,
            patch.object(SupervisorAI, "validate_html", new_callable=AsyncMock) as vh,
            patch.object(SupervisorAI, "validate_deployment", new_callable=AsyncMock) as vd,
            patch.object(SupervisorAI, "validate_database", new_callable=AsyncMock) as vdb,
            patch.object(SupervisorAI, "validate_payment", new_callable=AsyncMock) as vp,
        ):
            vb.return_value = {"valid": True, "errors": []}
            vh.return_value = {"valid": True, "errors": [], "warnings": []}
            vd.return_value = {"valid": True, "errors": []}
            vdb.return_value = {"valid": True, "errors": []}
            vp.return_value = {"valid": True, "errors": []}

            result = await run_pipeline(
                PipelineRequest(
                    prompt=brief["description"],
                    project_type=brief["project_type"],
                    client_name=brief["client_name"],
                ),
                generation_id=gid,
            )

    session = generation_event_store.get_session(gid)
    if session is None:
        errors.append("session SSE absente")
        return errors

    starts = [e for e in session.history if e[1] == "agent_start"]
    agents = [e[2].get("agent") for e in starts]
    totals = {e[2].get("total") for e in starts}

    if agents != ["BriefAI", "DesignSystemAI", "GeneratorAI", "SupervisorAI", "DeployAI"]:
        errors.append(f"ordre agents SSE incorrect: {agents}")
    if totals != {TRACKED_TOTAL} or TRACKED_TOTAL != 5:
        errors.append(f"total SSE attendu 5, obtenu {totals}")

    final_html = str(result.get("html") or "")
    if ":root" not in final_html or "--color-primary" not in final_html:
        injected = inject_design_system_into_html(html, result.get("brief", {}).get("design_system") or {})
        if ":root" not in injected:
            errors.append("HTML final sans :root / --color-primary")

    await generation_event_store.cleanup(gid)
    return errors


async def main() -> int:
    failed = 0
    for scenario in SCENARIOS:
        name = scenario["name"]
        brief = scenario["brief"]
        print(f"\n=== {name} ===")
        checks = _check_design_system(brief, scenario["expected_family"])
        checks.extend(await _check_pipeline_sse(brief, brief["client_name"]))
        if checks:
            failed += 1
            for err in checks:
                print(f"  FAIL: {err}")
        else:
            print("  OK (5 checks)")
    print(f"\n{'ÉCHEC' if failed else 'SUCCÈS'}: {len(SCENARIOS) - failed}/{len(SCENARIOS)} scénarios")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

"""
Validation pipeline V2 extension_navigateur (sans LLM — BriefAI mocké).

Usage (depuis backend/) :
    python scripts/validate_extension_v2_e2e.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from agents.deploy_ai import build_extension_demo_page
from api.generation_stream import generation_event_store
from pipeline import PipelineRequest, run_pipeline
from tools.extension_pipeline import build_extension_files, resolve_extension_sector_id

SCENARIOS: dict[str, dict[str, Any]] = {
    "ecommerce-helper": {
        "client_name": "ShopSmart",
        "couleur_primaire": "#f59e0b",
        "sector": "ecommerce-helper",
        "sector_markers": ["Comparer", "cf_history", "compare"],
    },
    "productivite": {
        "client_name": "FocusFlow",
        "couleur_primaire": "#8b5cf6",
        "sector": "productivite",
        "sector_markers": ["Pomodoro", "cf_tasks", "cf_blocks"],
    },
    "seo-analytics": {
        "client_name": "SEOLens",
        "couleur_primaire": "#06b6d4",
        "sector": "seo-analytics",
        "sector_markers": ["cf_seo_analyze", "scoreArc", "metaPanel"],
    },
}

REQUIRED_FILES = {
    "manifest.json",
    "popup.html",
    "popup.js",
    "background.js",
    "content.js",
    "README.md",
}


def _check_zip(files: dict[str, str]) -> tuple[bool, str, bytes]:
    from tools.extension_pipeline import build_extension_zip

    data = build_extension_zip(files)
    with zipfile.ZipFile(BytesIO(data)) as zf:
        names = set(zf.namelist())
    missing = REQUIRED_FILES - names
    if missing:
        return False, f"fichiers manquants: {missing}", data
    return True, f"6 fichiers OK ({len(data)} octets)", data


def _check_manifest(files: dict[str, str]) -> tuple[bool, str]:
    manifest = json.loads(files["manifest.json"])
    if manifest.get("manifest_version") != 3:
        return False, "manifest_version != 3"
    return True, "MV3 valide"


def _check_tabs(html: str) -> tuple[bool, str]:
    count = html.lower().count('class="tab')
    if count < 3:
        return False, f"moins de 3 tabs ({count})"
    return True, f"{count} tabs"


def _check_sector_js(js: str, markers: list[str]) -> tuple[bool, str]:
    hits = sum(1 for m in markers if m in js)
    if hits < 2:
        return False, f"logique secteur insuffisante ({hits}/{len(markers)})"
    return True, f"logique secteur OK ({hits} marqueurs)"


def _check_primary(html: str, color: str) -> tuple[bool, str]:
    if color.lower() in html.lower() or color in html:
        return True, f"{color} present"
    return False, f"{color} absent du popup"


def _check_demo_page(name: str, color: str) -> tuple[bool, str]:
    html = build_extension_demo_page(
        extension_name=name,
        client_name=name,
        primary_color=color,
    )
    if "extension.zip" not in html:
        return False, "lien ZIP absent"
    if name not in html:
        return False, "nom extension absent"
    if "#0f1117" not in html:
        return False, "design dark absent"
    return True, "page demo OK"


async def run_scenario(sector_key: str) -> tuple[bool, list[str]]:
    cfg = SCENARIOS[sector_key]
    brief = {
        "client_name": cfg["client_name"],
        "project_type": "extension_navigateur",
        "sector": cfg["sector"],
        "couleur_primaire": cfg["couleur_primaire"],
        "description": f"Extension test {sector_key}",
        "prompt": f"Extension {cfg['client_name']}",
    }

    assert resolve_extension_sector_id(brief) == sector_key

    files = build_extension_files(brief)
    logs: list[str] = []

    ok_zip, detail_zip, _zip_data = _check_zip(files)
    ok_man, detail_man = _check_manifest(files)
    ok_tabs, detail_tabs = _check_tabs(files["popup.html"])
    ok_js, detail_js = _check_sector_js(files["popup.js"], cfg["sector_markers"])
    ok_pri, detail_pri = _check_primary(files["popup.html"], cfg["couleur_primaire"])
    ok_demo, detail_demo = _check_demo_page(cfg["client_name"], cfg["couleur_primaire"])
    checks = [
        ("1_zip", ok_zip, detail_zip),
        ("2_manifest", ok_man, detail_man),
        ("3_tabs", ok_tabs, detail_tabs),
        ("4_sector_js", ok_js, detail_js),
        ("5_primary", ok_pri, detail_pri),
        ("6_demo", ok_demo, detail_demo),
    ]

    all_ok = True
    for name, ok, detail in checks:
        status = "PASS" if ok else "FAIL"
        logs.append(f"  [{status}] {name}: {detail}")
        if not ok:
            all_ok = False

    gid = f"ext-v2-{sector_key}-{uuid4().hex[:8]}"
    await generation_event_store.create(gid)

    mock_brief = {**brief, "client_name": cfg["client_name"]}

    async def _fake_supervised(_agent, run_once, _validate, **kwargs):
        del _validate, kwargs
        return await run_once("")

    with (
        patch("pipeline.BriefAI") as brief_cls,
        patch("pipeline.DeployAI") as dep_cls,
        patch("pipeline._run_supervised", side_effect=_fake_supervised),
    ):
        brief_cls.return_value.run = AsyncMock(return_value=mock_brief)

        dep_cls.return_value.run_extension = AsyncMock(
            return_value={
                "url": f"https://demo.test/{sector_key}",
                "success": True,
                "html": build_extension_demo_page(
                    extension_name=cfg["client_name"],
                    client_name=cfg["client_name"],
                    primary_color=cfg["couleur_primaire"],
                ),
                "unlock_url": f"https://demo.test/{sector_key}",
                "demo_token": "tok",
            }
        )

        result = await run_pipeline(
            PipelineRequest(
                prompt=f"Extension {cfg['client_name']}",
                project_type="extension_navigateur",
                client_name=cfg["client_name"],
            ),
            generation_id=gid,
        )

    session = generation_event_store.get_session(gid)
    done_agents = [
        e[2].get("agent")
        for e in (session.history if session else [])
        if e[1] == "agent_done"
    ]
    sse_ok = done_agents == ["BriefAI", "ExtensionBuilder", "DeployAI"]
    status = "PASS" if sse_ok else "FAIL"
    logs.append(f"  [{status}] 7_sse: {done_agents}")
    if not sse_ok:
        all_ok = False
    if not result.get("success"):
        logs.append("  [FAIL] pipeline success=False")
        all_ok = False

    await generation_event_store.cleanup(gid)
    return all_ok, logs


async def main() -> int:
    print("=== Validation extension V2 ===\n")
    results: dict[str, bool] = {}
    for sector in SCENARIOS:
        print(f"[{sector}]")
        ok, logs = await run_scenario(sector)
        for line in logs:
            print(line)
        results[sector] = ok
        print()

    print("=== RESUME ===")
    for sector, ok in results.items():
        print(f"  {sector}: {'OK' if ok else 'ECHEC'}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

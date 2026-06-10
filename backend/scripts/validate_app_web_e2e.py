"""
Validation E2E App web — génère du HTML réel via DatabaseAI + AuthAI + GeneratorAI.

Usage (depuis backend/) :
    python scripts/validate_app_web_e2e.py
    python scripts/validate_app_web_e2e.py --sector crm-clients
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path
from typing import Any

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from agents import auth_ai, database_ai
from agents.generator_ai import GeneratorAI
from config import get_settings
from security.llm_secrets import get_effective_llm_key

SCENARIOS: dict[str, dict[str, Any]] = {
    "crm-clients": {
        "client_name": "CapCore CRM",
        "couleur_primaire": "#6366f1",
        "couleur_secondaire": "#312e81",
        "sector": "CRM / clients",
        "description": "CRM interne pour gérer les prospects et clients CapCore",
        "extra_checks": [],
    },
    "stock-inventaire": {
        "client_name": "CapCore Stock",
        "couleur_primaire": "#10b981",
        "couleur_secondaire": "#064e3b",
        "sector": "stock / inventaire",
        "description": "Gestion de stocks et inventaires multi-dépôts CapCore",
        "extra_checks": ["stock_badge"],
    },
}


def _check_login_screen_visible(html: str) -> tuple[bool, str]:
    if 'id="login-screen"' not in html and "id='login-screen'" not in html:
        return False, "id=login-screen manquant"
    if re.search(
        r'id=["\']login-screen["\'][^>]*style=["\'][^"\']*display\s*:\s*none',
        html,
        re.I,
    ):
        return False, "login-screen caché par défaut dans style inline"
    return True, "ok"


def _check_app_shell_hidden(html: str) -> tuple[bool, str]:
    if 'id="app-shell"' not in html and "id='app-shell'" not in html:
        return False, "id=app-shell manquant"
    low = html.lower()
    idx = low.find('id="app-shell"')
    if idx == -1:
        idx = low.find("id='app-shell'")
    snippet = html[idx : idx + 400].lower()
    if "display:none" in snippet.replace(" ", "") or "display: none" in snippet:
        return True, "ok"
    if re.search(r'#app-shell\s*\{[^}]*display\s*:\s*none', html, re.I | re.S):
        return True, "ok"
    return False, "app-shell pas caché par défaut"


def _check_sidebar_nav(html: str) -> tuple[bool, str]:
    nav_items = len(re.findall(r'class=["\'][^"\']*nav-item', html, re.I))
    nav_items += len(re.findall(r'data-view=["\']view-', html, re.I))
    if nav_items < 3:
        return False, f"sidebar nav items insuffisants ({nav_items})"
    return True, f"{nav_items} items nav"


def _check_views_switcher(html: str) -> tuple[bool, str]:
    views = set(re.findall(r'id=["\'](view-[^"\']+)["\']', html, re.I))
    if len(views) < 3:
        return False, f"vues insuffisantes ({len(views)}: {views})"
    if "showview" not in html.lower().replace(" ", ""):
        return False, "fonction showView manquante"
    return True, f"{len(views)} vues"


def _check_client_data(html: str) -> tuple[bool, str]:
    if "<table" in html.lower() or "tableau" in html.lower():
        rows = len(re.findall(r"<tr\b", html, re.I))
        if rows >= 3:
            return True, f"tableau {rows} lignes"
    cards = len(re.findall(r'class=["\'][^"\']*card', html, re.I))
    list_items = len(re.findall(r"<li\b", html, re.I))
    if cards >= 3 or list_items >= 5:
        return True, f"liste/cards ({cards} cards, {list_items} li)"
    return False, "pas de tableau/liste avec données fictives"


def _check_form(html: str) -> tuple[bool, str]:
    forms = len(re.findall(r"<form\b", html, re.I))
    if forms >= 1:
        return True, f"{forms} formulaire(s)"
    inputs = len(re.findall(r"<input\b", html, re.I))
    if inputs >= 3:
        return True, f"{inputs} champs input"
    return False, "formulaire manquant"


def _check_auth_schema_used(html: str, auth_schema: dict[str, Any]) -> tuple[bool, str]:
    roles = auth_schema.get("roles") or []
    auth_type = str(auth_schema.get("auth_type") or "")
    tables = auth_schema.get("tables") or []
    if isinstance(auth_schema.get("database_schema"), dict):
        tables = auth_schema["database_schema"].get("tables") or tables

    hits = 0
    low = html.lower()
    if auth_type and auth_type.replace("_", " ") in low.replace("_", " "):
        hits += 1
    if auth_type and auth_type in low:
        hits += 1
    for role in roles:
        if str(role).lower() in low:
            hits += 1
    for t in (tables if isinstance(tables, list) else []):
        name = t.get("name") if isinstance(t, dict) else str(t)
        if name and str(name).lower() in low:
            hits += 1
    if hits >= 1:
        return True, f"{hits} références auth/schema"
    summary = str(auth_schema.get("summary") or "").lower()
    if summary and any(w in low for w in summary.split()[:3] if len(w) > 4):
        return True, "summary référencé"
    return False, "auth_schema/database_schema non reflété dans l'UI"


def _check_dark_design(html: str) -> tuple[bool, str]:
    if "#0f1117" in html.lower() or "0f1117" in html.lower():
        return True, "#0f1117 présent"
    if "#161b27" in html.lower():
        return True, "#161b27 présent"
    if re.search(r"background\s*:\s*#[0-1][0-9a-f]{5}", html, re.I):
        return True, "fond sombre détecté"
    return False, "design dark absent"


def _check_stock_badge(html: str) -> tuple[bool, str]:
    low = html.lower()
    for term in ("disponible", "faible", "rupture"):
        if term in low:
            return True, f"badge stock ({term})"
    return False, "badges stock (Disponible/Faible/Rupture) absents"


CHECKS = [
    ("1_login_screen", _check_login_screen_visible),
    ("2_app_shell_hidden", _check_app_shell_hidden),
    ("3_sidebar_nav", _check_sidebar_nav),
    ("4_views_switcher", _check_views_switcher),
    ("5_client_data", _check_client_data),
    ("6_form", _check_form),
    ("7_auth_schema", None),  # needs auth_schema arg
    ("8_dark_design", _check_dark_design),
]


async def run_scenario(sector_key: str) -> bool:
    cfg = SCENARIOS[sector_key]
    settings = get_settings()
    if not get_effective_llm_key("ANTHROPIC_API_KEY", settings):
        print(f"[{sector_key}] SKIP — ANTHROPIC_API_KEY absente")
        return False

    brief: dict[str, Any] = {
        "client_name": cfg["client_name"],
        "project_type": "application_web",
        "sector": cfg["sector"],
        "description": cfg["description"],
        "couleur_primaire": cfg["couleur_primaire"],
        "couleur_secondaire": cfg["couleur_secondaire"],
        "prompt": (
            f"Client : {cfg['client_name']}\n"
            f"Secteur : {cfg['sector']}\n"
            f"Description : {cfg['description']}\n"
            f"Couleur primaire : {cfg['couleur_primaire']}\n"
        ),
    }

    print(f"\n[{sector_key}] DatabaseAI...")
    brief["database_schema"] = await database_ai.run(
        project_description=cfg["description"],
        project_type="application_web",
        design_system={},
    )
    print(f"  -> {len(brief['database_schema'].get('tables') or [])} table(s)")

    print(f"[{sector_key}] AuthAI...")
    brief["auth_schema"] = await auth_ai.run(
        project_description=cfg["description"],
        project_type="application_web",
        database_schema=brief["database_schema"],
    )
    print(f"  -> auth_type={brief['auth_schema'].get('auth_type')}")

    print(f"[{sector_key}] GeneratorAI...")
    gen = GeneratorAI()
    result = await gen.run(brief)
    if not result.get("success") or not result.get("html"):
        print(f"[{sector_key}] ECHEC generation")
        return False

    html = result["html"]
    print(f"  -> {len(html)} caracteres")

    out_dir = _BACKEND_ROOT / "scripts" / "output"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"app_web_{sector_key}.html"
    out_file.write_text(html, encoding="utf-8")
    print(f"  -> sauvegarde {out_file}")

    auth_ctx = {
        **brief["auth_schema"],
        "database_schema": brief["database_schema"],
    }
    all_ok = True
    for name, fn in CHECKS:
        if fn is None:
            ok, detail = _check_auth_schema_used(html, auth_ctx)
        else:
            ok, detail = fn(html)
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}: {detail}")
        if not ok:
            all_ok = False

    for extra in cfg.get("extra_checks", []):
        if extra == "stock_badge":
            ok, detail = _check_stock_badge(html)
            status = "PASS" if ok else "FAIL"
            print(f"  [{status}] stock_badge: {detail}")
            if not ok:
                all_ok = False

    return all_ok


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sector",
        choices=list(SCENARIOS.keys()),
        default=None,
        help="Secteur unique (défaut : tous)",
    )
    args = parser.parse_args()
    sectors = [args.sector] if args.sector else list(SCENARIOS.keys())

    results: dict[str, bool] = {}
    for sector in sectors:
        results[sector] = await run_scenario(sector)

    print("\n=== RESUME ===")
    for sector, ok in results.items():
        print(f"  {sector}: {'OK' if ok else 'ECHEC'}")

    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

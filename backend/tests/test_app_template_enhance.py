"""Tests routage slots app + script interactions app_*."""

from __future__ import annotations

from pathlib import Path

from agents.content_slots import build_app_slots
from tools.app_template_enhance import enhance_app_template_html
from agents.template_ai import load_sector_template_html


def test_build_app_slots_garage_stats() -> None:
    slots = build_app_slots(
        "app_dashboard",
        "Garage Dupont",
        {"PRIMARY_COLOR": "#2563EB"},
        "automobile",
        user_prompt="garage réparation véhicules",
    )
    assert slots["STAT_1_LABEL"] == "Réparations en cours"
    assert slots["STAT_2_LABEL"] == "Véhicules au parc"
    assert slots["TABLE_TITLE"] == "Interventions récentes"
    assert slots["COL_1"] == "Véhicule"


def test_enhance_app_injects_cf_ui_script() -> None:
    raw = load_sector_template_html("app_dashboard.html")
    out = enhance_app_template_html(raw)
    assert 'id="cf-app-ui"' in out
    assert 'id="cf-app-sections"' in out
    assert "cf-edit-row" in out
    assert out.count('id="cf-app-ui"') == 1
    out2 = enhance_app_template_html(out)
    assert out2.count('id="cf-app-ui"') == 1


def test_app_templates_have_interactive_markup() -> None:
    sectors = Path(__file__).resolve().parents[1] / "templates" / "sectors"
    dash = (sectors / "app_dashboard.html").read_text(encoding="utf-8")
    assert "window.openModal = function" in dash
    assert "window.confirmDelete = function" in dash
    for name in ("app_crm.html", "app_default.html"):
        html = (sectors / name).read_text(encoding="utf-8")
        assert "cf-edit-row" in html
        assert "cf-del-row" in html
        assert "data-cf-section" in html
        assert "openM(" not in html
        assert "function(){openM" not in html


def test_app_dashboard_garage_sidebar_sections() -> None:
    path = Path(__file__).resolve().parents[1] / "templates" / "sectors" / "app_dashboard.html"
    html = path.read_text(encoding="utf-8")
    for section in (
        "dashboard",
        "interventions",
        "devis",
        "factures",
        "clients",
        "vehicules",
        "equipe",
        "parametres",
    ):
        assert f'id="{section}"' in html
        assert f"showSection('{section}')" in html
    assert "window.openModal = function" in html
    assert "window.confirmDelete = function" in html
    assert 'id="tableBody"' in html
    assert 'id="modalOverlay"' in html

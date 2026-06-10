"""Tests templates extension par secteur."""

from __future__ import annotations

import json

from tools.extension_pipeline import build_extension_files, resolve_extension_sector_id


def _brief(sector: str, name: str, color: str) -> dict:
    return {
        "client_name": name,
        "sector": sector,
        "couleur_primaire": color,
        "description": f"Extension {name}",
        "prompt": f"Extension {name}",
    }


def test_ecommerce_helper_sector() -> None:
    brief = _brief("ecommerce-helper", "ShopSmart", "#f59e0b")
    assert resolve_extension_sector_id(brief) == "ecommerce-helper"
    files = build_extension_files(brief)
    assert "Comparer" in files["popup.html"]
    assert "btnCompare" in files["popup.js"]
    assert "#f59e0b" in files["popup.html"]
    manifest = json.loads(files["manifest.json"])
    assert manifest["manifest_version"] == 3
    assert "storage" in manifest["permissions"]


def test_productivite_sector() -> None:
    brief = _brief("productivite", "FocusFlow", "#8b5cf6")
    assert resolve_extension_sector_id(brief) == "productivite"
    files = build_extension_files(brief)
    assert "Pomodoro" in files["popup.html"]
    assert "cf_tasks" in files["popup.js"]
    assert "alarms" in files["manifest.json"]


def test_seo_analytics_sector() -> None:
    brief = _brief("seo-analytics", "SEOLens", "#06b6d4")
    assert resolve_extension_sector_id(brief) == "seo-analytics"
    files = build_extension_files(brief)
    assert "Méta" in files["popup.html"] or "meta" in files["popup.html"].lower()
    assert "cf_seo_analyze" in files["content.js"]
    assert "#06b6d4" in files["popup.html"]

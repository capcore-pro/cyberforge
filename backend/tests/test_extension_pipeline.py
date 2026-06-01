"""Tests pipeline extension_navigateur (MV3, ZIP, pas template-first)."""

from __future__ import annotations

import json
import zipfile
from io import BytesIO

from agents.architect_agent import ArchitectPlan, ToolboxPalette
from agents.coremind_agent import ProjectType
from agents.template_first_policy import is_template_first_html_project
from tools.extension_pipeline import (
    build_extension_export_manifest,
    build_extension_files,
    build_extension_zip,
    extract_extension_display_name,
    extract_extension_popup_html,
    is_extension_project_type,
    prepare_extension_preview_html,
)
from tools.sector_template_catalog import (
    resolve_sector_template_from_plan,
    resolve_template_family_from_plan,
)


def _plan(pt: ProjectType = ProjectType.EXTENSION_NAVIGATEUR) -> ArchitectPlan:
    return ArchitectPlan(
        project_type=pt,
        project_type_label="Extension",
        template="extension",
        template_label="Extension Chrome",
        rationale="Test",
        complexity_score=3,
        complexity_label="Moyenne",
        market_price_min=500,
        market_price_max=2000,
        suggested_price_min=200,
        suggested_price_max=800,
        palette=ToolboxPalette(primary="#2563EB", secondary="#F8FAFC", accent="#F59E0B"),
        pricing_category="extension_navigateur",
    )


def test_extension_family_never_ecommerce_or_vitrine() -> None:
    plan = _plan()
    assert resolve_template_family_from_plan(plan) == "extension"
    tid, fname = resolve_sector_template_from_plan(
        plan, "commerce", "boutique ecommerce en ligne"
    )
    assert tid == "extension_chrome"
    assert fname == "extension_chrome.html"
    assert not tid.startswith("ecommerce_")
    assert not fname.startswith("vitrine_")


def test_extension_not_template_first() -> None:
    plan = _plan()
    assert is_template_first_html_project(plan, generation_mode="client_demo") is False


def test_build_extension_files_manifest_and_popup() -> None:
    files = build_extension_files("extension pour bloquer les pubs")
    assert "manifest.json" in files
    assert "popup.html" in files
    assert "background.js" in files
    assert "content.js" in files
    manifest = json.loads(files["manifest.json"])
    assert manifest["manifest_version"] == 3
    assert manifest["action"]["default_popup"] == "popup.html"
    assert "380px" in files["popup.html"]
    assert "500px" in files["popup.html"]


def test_extension_zip_contains_all_files() -> None:
    files = build_extension_files("test zip")
    data = build_extension_zip(files)
    with zipfile.ZipFile(BytesIO(data)) as zf:
        names = set(zf.namelist())
    assert "manifest.json" in names
    assert "popup.html" in names
    assert "background.js" in names
    assert "content.js" in names


def test_is_extension_project_type() -> None:
    assert is_extension_project_type(_plan()) is True
    site = _plan(ProjectType.SITE_WEB)
    site.pricing_category = "site_web"
    assert is_extension_project_type(site) is False


def test_extension_export_manifest_has_no_cloud_deploy_fields() -> None:
    manifest = build_extension_export_manifest(
        project_id="my-ext",
        project_type_label="Extension",
        files=["manifest.json", "popup.html"],
        zip_bytes=1024,
        download_url="/api/pipeline/extension-artifact/my-ext",
    )
    assert manifest["provider"] == "zip"
    assert manifest["artifact_type"] == "chrome_extension_zip"
    assert "domain" not in manifest
    assert "env" not in manifest
    assert manifest["download_url"].endswith("my-ext")


def test_extract_extension_display_name_from_quotes() -> None:
    name = extract_extension_display_name(
        "TYPE: extension_navigateur\nCréer l'extension 'CleanShop' pour bloquer les pubs"
    )
    assert name == "CleanShop"


def test_extract_extension_display_name_from_nom_label() -> None:
    name = extract_extension_display_name("Nom : TabSaver Pro — gestion onglets")
    assert name == "TabSaver Pro"


def test_extract_extension_display_name_keywords_not_full_prompt() -> None:
    prompt = (
        "extension chrome pour nettoyer les cookies et améliorer la confidentialité "
        "sur tous les sites visités chaque jour"
    )
    name = extract_extension_display_name(prompt)
    assert len(name) < 60
    assert "extension chrome pour" not in name.lower()


def test_extract_extension_popup_html_from_files() -> None:
    files = build_extension_files("popup test")
    popup, js = extract_extension_popup_html(extension_files=files)
    assert "<!DOCTYPE html>" in popup
    assert "toggleMaster" in js


def test_prepare_extension_preview_inlines_js_and_chrome_shim() -> None:
    files = build_extension_files("popup test")
    preview = prepare_extension_preview_html(
        files["popup.html"],
        popup_js=files["popup.js"],
        prompt="Extension 'CleanShop' pour bloquer les publicités",
    )
    assert "380" in preview
    assert 'src="popup.js"' not in preview
    assert "cf-extension-preview-shim" in preview
    assert "cf-extension-preview-shell" in preview
    assert "max-width: 380px" in preview
    assert "CleanShop" in preview
    assert "toggleMaster" in preview
    assert "Extension 'CleanShop' pour" not in preview

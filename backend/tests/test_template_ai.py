"""Tests TemplateAI — sélection et remplissage templates sectoriels."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from agents.coremind_agent import ProjectType
from agents.design_system_ai import build_design_system
from agents.template_ai import (
    _TEMPLATES_DIR,
    fill_template_placeholders,
    load_sector_template_html,
    render_sector_template,
    resolve_sector_template_file,
)
from core.agent_contract import require_ok

REQUIRED_PLACEHOLDERS = {
    "CLIENT_NAME",
    "SECTOR",
    "CITY",
    "PRIMARY_COLOR",
    "SECONDARY_COLOR",
    "FONT_HEADING",
    "FONT_BODY",
    "HERO_TITLE",
    "HERO_SUBTITLE",
    "SERVICE_1",
    "SERVICE_2",
    "SERVICE_3",
    "CTA_TEXT",
    "PHONE",
    "EMAIL",
    "ADDRESS",
    "GOOGLE_FONTS_URL",
}


@pytest.mark.parametrize(
    "prompt,expected",
    [
        ("boulangerie artisanale", "vitrine_alimentaire"),
        ("plombier urgence", "vitrine_artisan"),
        ("cabinet dentaire", "vitrine_sante"),
        ("salon coiffure", "vitrine_beaute"),
        ("école de voile", "vitrine_nautisme"),
        ("consulting général", "vitrine_default"),
    ],
)
def test_resolve_template_file(prompt: str, expected: str) -> None:
    _tid, filename = resolve_sector_template_file("commerce", prompt)
    assert filename == f"{expected}.html"


def test_all_sector_templates_exist() -> None:
    for name in (
        "vitrine_alimentaire.html",
        "vitrine_artisan.html",
        "vitrine_sante.html",
        "vitrine_beaute.html",
        "vitrine_nautisme.html",
        "vitrine_default.html",
    ):
        assert (_TEMPLATES_DIR / name).is_file()


def test_render_boulangerie_complete() -> None:
    ds = require_ok(
        build_design_system(
            sector="restauration",
            client_name="Aux Délices",
            project_type=ProjectType.SITE_WEB,
            user_prompt="Boulangerie à Rouen",
        )
    )
    result = render_sector_template(
        sector="restauration",
        user_prompt="Boulangerie patisserie Aux Délices Rouen",
        design_system=ds.to_contract_dict(),
    )
    data = require_ok(result)
    assert data.template_id == "vitrine_alimentaire"
    assert "Aux Délices" in data.html
    assert "{{" not in data.html


def test_placeholders_in_raw_template() -> None:
    raw = load_sector_template_html("vitrine_default.html")
    found = set()
    import re

    for m in re.finditer(r"\{\{([A-Z0-9_]+)\}\}", raw):
        found.add(m.group(1))
    assert REQUIRED_PLACEHOLDERS.issubset(found)


def test_fill_leaves_no_placeholders() -> None:
    raw = load_sector_template_html("vitrine_artisan.html")
    slots = {k: f"VAL_{k}" for k in REQUIRED_PLACEHOLDERS}
    html, _, missing = fill_template_placeholders(raw, slots)
    assert not missing
    assert "{{" not in html


def test_agent_async() -> None:
    from agents.template_ai import TemplateAgent

    agent = TemplateAgent()

    async def _run():
        return await agent.load(
            sector="beaute",
            user_prompt="Coiffeur Salon Éclat",
            design_system=require_ok(
                build_design_system(
                    sector="beaute",
                    client_name="Salon Éclat",
                    project_type=ProjectType.SITE_WEB,
                )
            ).to_contract_dict(),
        )

    result = asyncio.run(_run())
    assert result.ok
    assert result.data.template_id == "vitrine_beaute"  # type: ignore[union-attr]

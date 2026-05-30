"""Tests intégration toolbox dans ArchitectAI."""

import asyncio

from agents.architect_agent import ArchitectAgent
from tools.toolbox_sectors import detect_sector_from_prompt, get_sector_bundle


def test_detect_restauration_from_prompt() -> None:
    key = detect_sector_from_prompt("Boulangerie artisanale à Lyon, menu et contact")
    assert key == "restauration"
    bundle = get_sector_bundle(key)
    assert bundle is not None
    assert bundle.palette["primary"] == "#8B2E1F"
    assert "hero" in bundle.composants


def test_architect_plan_includes_toolbox_fields() -> None:
    agent = ArchitectAgent()
    plan, _ = asyncio.run(
        agent.plan_with_analysis("Restaurant gastronomique avec carte des vins à Bordeaux")
    )
    assert plan.secteur == "restauration"
    assert plan.palette is not None
    assert plan.typo is not None
    assert plan.composants_recommandes
    assert len(plan.palette.primary) == 7

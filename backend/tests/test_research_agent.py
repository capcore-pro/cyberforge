"""Tests extraction contexte ResearchAI."""

from __future__ import annotations

from agents.architect_agent import ArchitectPlan
from agents.coremind_agent import ProjectType
from agents.research_agent import (
    extract_research_context,
    format_research_brief_for_prompt,
    ResearchBrief,
)


def _plan(**kwargs: object) -> ArchitectPlan:
    defaults = dict(
        project_type=ProjectType.SITE_WEB,
        project_type_label="Site web",
        template="taskflow",
        template_label="TaskFlow",
        rationale="Test",
        complexity_score=5,
        complexity_label="Moyenne",
        market_price_min=1000,
        market_price_max=3000,
        suggested_price_min=400,
        suggested_price_max=1200,
    )
    defaults.update(kwargs)
    return ArchitectPlan(**defaults)  # type: ignore[arg-type]


def test_extract_city_and_company() -> None:
    prompt = 'Site vitrine pour restaurant "La Table du Port" à Marseille'
    ctx = extract_research_context(prompt, plan=_plan(secteur="restauration"))
    assert ctx["ville"] == "Marseille"
    assert "Table du Port" in ctx["nom_entreprise"] or ctx["nom_entreprise"]


def test_format_research_brief_for_prompt() -> None:
    brief = ResearchBrief(
        secteur="restauration",
        nom_entreprise="La Table",
        ville="Lyon",
        type_projet="Site web",
        tendances=["Menu digital"],
        mots_cles=["restaurant", "lyon"],
    )
    block = format_research_brief_for_prompt(brief)
    assert "Brief recherche contenu" in block
    assert "Menu digital" in block
    assert "restaurant" in block

"""Tests injection brief ResearchAI."""

from agents.research_agent import ResearchBrief, format_research_brief_for_prompt


def test_format_brief_with_client_context_only() -> None:
    brief = ResearchBrief(
        secteur="plomberie",
        nom_entreprise="Dupont Chauffage",
        ville="Lyon",
        type_projet="site vitrine",
    )
    block = format_research_brief_for_prompt(brief)
    assert "Dupont Chauffage" in block
    assert "plomberie" in block
    assert "Lyon" in block


def test_format_brief_skipped_empty() -> None:
    brief = ResearchBrief(skipped=True, skip_reason="off")
    assert format_research_brief_for_prompt(brief) == ""

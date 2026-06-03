"""Tests registre central des prompts BuilderAI v2."""

from prompts import (
    BUILDER_DEEPSEEK_SYSTEM,
    BUILDER_V0_SYSTEM,
    CODEGEN_DEMO_HTML_PROMPT,
    CODEGEN_SYSTEM_PROMPT,
    CONTENT_AI_SYSTEM_PROMPT,
    DEMO_SEED_SYSTEM_PROMPT,
    PERSONALIZED_CONTENT_DIRECTIVE,
    PROMPTS_VERSION,
    VITRINE_CONTENT_SYSTEM,
    build_autofix_prompt,
)


def test_prompts_version_defined() -> None:
    assert PROMPTS_VERSION.startswith("2.")


def test_personalization_in_all_system_prompts() -> None:
    for prompt in (
        BUILDER_V0_SYSTEM,
        BUILDER_DEEPSEEK_SYSTEM,
        CODEGEN_SYSTEM_PROMPT,
        CODEGEN_DEMO_HTML_PROMPT,
        DEMO_SEED_SYSTEM_PROMPT,
        VITRINE_CONTENT_SYSTEM,
        CONTENT_AI_SYSTEM_PROMPT,
    ):
        assert "Jean Dupont" in prompt or "fictif" in prompt.lower()
        assert PERSONALIZED_CONTENT_DIRECTIVE.split("\n")[1] in prompt


def test_autofix_prompt_includes_personalization() -> None:
    text = build_autofix_prompt(
        "Site CapCore Pro",
        issues_text="- [missing_css] peu de CSS",
        attempt=1,
        max_attempts=3,
    )
    assert "CapCore Pro" in text
    assert "Jean Dupont" in text or "fictif" in text.lower()

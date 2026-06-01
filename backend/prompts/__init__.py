"""
Registre central des prompts LLM — BuilderAI v2.

Tous les prompts système sont versionnés ici. Les modules applicatifs
importent depuis ce package plutôt que de dupliquer des chaînes inline.
"""

from __future__ import annotations

from prompts.autofix import build_autofix_prompt
from prompts.builder import (
    BUILDER_DEEPSEEK_SYSTEM,
    BUILDER_V0_SYSTEM,
    SIMPLIFIED_VITRINE_DIRECTIVE,
)
from prompts.vitrine_html import BUILDER_VITRINE_HTML_DIRECTIVE, VITRINE_HTML_QUALITY_RULES
from prompts.codegen import (
    CODEGEN_DEMO_HTML_PROMPT,
    CODEGEN_SYSTEM_PROMPT,
    DEMO_SEED_SYSTEM_PROMPT,
    MAX_USER_PROMPT_CHARS,
)
from prompts.shared import (
    PERSONALIZED_CONTENT_DIRECTIVE,
    PROMPTS_VERSION,
    with_personalization,
)
from prompts.openhands import OPENHANDS_ANTHROPIC_SYSTEM, OPENHANDS_TASK_TEMPLATE
from prompts.vitrine import VITRINE_CONTENT_SYSTEM

__all__ = [
    "PROMPTS_VERSION",
    "PERSONALIZED_CONTENT_DIRECTIVE",
    "with_personalization",
    "BUILDER_V0_SYSTEM",
    "BUILDER_DEEPSEEK_SYSTEM",
    "SIMPLIFIED_VITRINE_DIRECTIVE",
    "BUILDER_VITRINE_HTML_DIRECTIVE",
    "VITRINE_HTML_QUALITY_RULES",
    "CODEGEN_SYSTEM_PROMPT",
    "CODEGEN_DEMO_HTML_PROMPT",
    "DEMO_SEED_SYSTEM_PROMPT",
    "MAX_USER_PROMPT_CHARS",
    "VITRINE_CONTENT_SYSTEM",
    "OPENHANDS_ANTHROPIC_SYSTEM",
    "OPENHANDS_TASK_TEMPLATE",
    "build_autofix_prompt",
]

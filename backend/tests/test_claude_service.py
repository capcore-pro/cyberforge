"""Tests unitaires du service Claude."""

from tools.claude_service import (
    DEFAULT_CLAUDE_MODEL,
    ClaudeService,
    ClaudeServiceError,
    _parse_json_response,
    _to_code_result,
)


def test_default_model() -> None:
    service = ClaudeService()
    assert service.model == DEFAULT_CLAUDE_MODEL
    assert DEFAULT_CLAUDE_MODEL == "claude-sonnet-4-20250514"


def test_parse_json_response_strips_fence() -> None:
    raw = '```json\n{"summary": "ok", "code": "x", "files": []}\n```'
    data = _parse_json_response(raw)
    assert data["code"] == "x"


def test_to_code_result() -> None:
    data = {
        "summary": "App React",
        "code": "export {}",
        "files": [{"path": "src/App.tsx", "content": "export {}"}],
        "stack": ["react"],
    }
    result = _to_code_result(data, "claude-sonnet-4-20250514")
    assert result.model == "claude-sonnet-4-20250514"
    assert result.provider == "anthropic"
    assert len(result.files) == 1


def test_generate_rejects_short_prompt() -> None:
    import asyncio

    service = ClaudeService()
    try:
        asyncio.run(service.generate_code("ab"))
        raised = False
    except ClaudeServiceError:
        raised = True
    assert raised

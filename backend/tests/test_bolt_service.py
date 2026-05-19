"""Tests unitaires du service Bolt."""

import pytest

from tools.bolt_service import (
    BoltProvider,
    BoltService,
    BoltServiceError,
    _llm_to_result,
    _parse_llm_json,
)


def test_parse_llm_json_strips_markdown_fence() -> None:
    raw = '```json\n{"summary": "ok", "code": "x", "files": []}\n```'
    data = _parse_llm_json(raw)
    assert data["summary"] == "ok"


def test_llm_to_result_builds_files() -> None:
    data = {
        "summary": "Landing créée",
        "code": "export default function App() {}",
        "files": [{"path": "src/App.tsx", "content": "export default function App() {}"}],
        "stack": ["react"],
    }
    result = _llm_to_result(data, BoltProvider.OPENAI, "gpt-4o-mini")
    assert result.provider == BoltProvider.OPENAI
    assert len(result.files) == 1
    assert "react" in result.stack


def test_generate_rejects_empty_prompt() -> None:
    service = BoltService()
    with pytest.raises(BoltServiceError, match="3 caractères"):
        import asyncio

        asyncio.run(service.generate("  "))

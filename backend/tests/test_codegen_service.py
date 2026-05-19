"""Tests unitaires du routage CoreMindAI."""

from tools.codegen_service import (
    CodeGenComplexity,
    CodeGenService,
    _parse_json_response,
    _to_code_result,
    complexity_from_score,
)


def test_complexity_from_score() -> None:
    assert complexity_from_score(2) == CodeGenComplexity.FAIBLE
    assert complexity_from_score(5) == CodeGenComplexity.MOYENNE
    assert complexity_from_score(9) == CodeGenComplexity.ELEVEE


def test_model_chain_faible_excludes_sonnet() -> None:
    service = CodeGenService()
    chain = service._model_chain(CodeGenComplexity.FAIBLE)
    models = [m for _, m in chain]
    assert service._settings.coremind_sonnet_model not in models
    assert len(chain) == 3


def test_model_chain_elevee_includes_sonnet() -> None:
    service = CodeGenService()
    chain = service._model_chain(CodeGenComplexity.ELEVEE)
    models = [m for _, m in chain]
    assert service._settings.coremind_sonnet_model in models
    assert len(chain) == 4


def test_parse_json_response() -> None:
    raw = '{"summary": "x", "code": "y", "files": []}'
    assert _parse_json_response(raw)["code"] == "y"


def test_to_code_result_provider() -> None:
    data = {
        "summary": "ok",
        "code": "const x = 1",
        "files": [{"path": "a.ts", "content": "const x = 1"}],
        "stack": ["ts"],
    }
    result = _to_code_result(data, "deepseek", "deepseek-chat")
    assert result.provider == "deepseek"
    assert result.model == "deepseek-chat"

"""Tests unitaires du routage CoreMindAI."""

import json

from tools.codegen_service import (
    CodeGenComplexity,
    CodeGenService,
    _parse_json_response,
    _to_code_result,
    _trim_prompt,
    _utf8_json_body,
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


def test_generation_specs_limited_attempts() -> None:
    service = CodeGenService()
    specs = service._generation_specs(CodeGenComplexity.FAIBLE)
    assert len(specs) <= service._settings.coremind_max_provider_attempts


def test_http_timeout_uses_settings() -> None:
    service = CodeGenService()
    timeout = service._http_timeout()
    assert timeout.read == service._settings.coremind_llm_timeout_seconds


def test_trim_prompt() -> None:
    short = _trim_prompt("hello")
    assert short == "hello"
    long = "x" * 5000
    assert len(_trim_prompt(long)) < len(long)


def test_parse_json_response() -> None:
    raw = '{"summary": "x", "code": "y", "files": []}'
    assert _parse_json_response(raw)["code"] == "y"


def test_parse_json_markdown_fence() -> None:
    raw = 'Voici le résultat :\n```json\n{"summary": "s", "code": "c", "files": []}\n```'
    assert _parse_json_response(raw)["code"] == "c"


def test_parse_json_embedded_in_prose() -> None:
    raw = (
        "Analyse — projet vitrine.\n"
        '{"summary": "ok", "code": "export default function App() {}", '
        '"files": [{"path": "src/App.tsx", "content": "x"}]}'
    )
    parsed = _parse_json_response(raw)
    assert "App" in parsed["code"]


def test_parse_plain_code_fallback() -> None:
    raw = "```tsx\nexport const Hero = () => <section>Hi</section>;\n```"
    parsed = _parse_json_response(raw)
    assert "Hero" in parsed["code"]
    assert parsed["files"][0]["path"] == "src/App.tsx"


def test_utf8_json_body_preserves_unicode() -> None:
    payload = {"messages": [{"role": "user", "content": "Menu — spécialités café"}]}
    body, headers = _utf8_json_body(payload)
    assert headers["Content-Type"] == "application/json; charset=utf-8"
    decoded = json.loads(body.decode("utf-8"))
    assert decoded["messages"][0]["content"] == "Menu — spécialités café"


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

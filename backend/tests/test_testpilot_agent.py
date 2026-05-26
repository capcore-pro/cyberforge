"""Tests TestPilotAI — validation HTML."""

from agents.testpilot_agent import TestPilotAgent, validate_demo_html

_MIN_OK_HTML = """<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8"><title>Test</title>
<style>body{font-family:sans-serif;background:#111;color:#eee;padding:2rem}
.card{padding:1rem;border:1px solid #0fc}</style></head>
<body><main class="card"><h1>Demo</h1><p>Contenu visible pour le client final.</p>
<a href="https://example.com">Site</a>
<script>document.querySelector('h1').addEventListener('click',function(){this.style.color='#0fc';});</script>
</main></body></html>"""


def test_validate_ok_html() -> None:
    report = validate_demo_html(_MIN_OK_HTML)
    assert report.ok is True
    assert report.issues == []


def test_detect_broken_empty_link() -> None:
    html = _MIN_OK_HTML.replace(
        'href="https://example.com"',
        'href="#"',
    )
    report = validate_demo_html(html)
    assert report.ok is False
    assert any(i.code == "broken_link" for i in report.issues)


def test_detect_js_syntax_risk() -> None:
    html = _MIN_OK_HTML.replace(
        "<script>document.querySelector",
        "<script>function broken( { console.error('fail');",
    )
    report = validate_demo_html(html)
    assert report.ok is False
    assert any(i.code == "js_console_risk" for i in report.issues)


def test_agent_validate_generation() -> None:
    from tools.codegen_service import CodeGenerateResult

    gen = CodeGenerateResult(
        summary="test",
        code=_MIN_OK_HTML,
        model="test",
        provider="test",
    )
    agent = TestPilotAgent()
    report = agent.validate_generation(gen)
    assert report.ok is True

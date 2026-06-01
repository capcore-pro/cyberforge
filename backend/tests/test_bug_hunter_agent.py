"""Tests BugHunterAI — détection défauts HTML."""

import re

from agents.bug_hunter_agent import (
    BugHunterAgent,
    analyze_demo_html,
    analyze_vitrine_html,
)
from tools.standalone_demo_html import build_task_manager_standalone_html

_VITRINE_OK = """<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><title>Aux Délices — Boulangerie Rouen</title></head>
<body>
<h1>Aux Délices — Boulangerie Artisanale à Rouen</h1>
<section id="contact"><form><input type="email" name="email" /><button>Envoyer</button></form></section>
</body></html>"""

REACT_LEAK = """<!DOCTYPE html>
<html><head><title>X</title></head>
<body>
<p>export default function App() { const [x, setX] = useState(0); return null; }</p>
</body></html>"""


def test_analyze_ok_taskflow_html() -> None:
    html = build_task_manager_standalone_html(title="Test", sources="")
    report = analyze_demo_html(html)
    assert report.ok
    assert not report.issues


def test_detect_visible_source() -> None:
    report = analyze_demo_html(REACT_LEAK)
    assert not report.ok
    assert "visible_source" in report.issue_codes


def test_detect_react_files_in_generation() -> None:
    from tools.codegen_service import CodeGenerateResult, GeneratedFile

    gen = CodeGenerateResult(
        summary="x",
        code="export default function App() {}",
        files=[GeneratedFile(path="src/App.tsx", content="export default function App() {}")],
        stack=["react"],
        model="t",
        provider="t",
    )
    report = BugHunterAgent().analyze_generation(gen, title="Test")
    assert not report.ok
    assert "visible_source" in report.issue_codes


def test_bug_hunter_agent_analyze_html() -> None:
    agent = BugHunterAgent()
    report = agent.analyze_html("<html><body></body></html>")
    assert not report.ok
    assert "render_error" in report.issue_codes or "empty_elements" in report.issue_codes


def test_vitrine_ok_minimal() -> None:
    report = analyze_vitrine_html(_VITRINE_OK)
    assert report.ok
    assert not report.issues


def test_vitrine_blocks_unresolved_placeholder() -> None:
    html = _VITRINE_OK.replace("</h1>", " {{HERO_TITLE}}</h1>")
    report = analyze_vitrine_html(html)
    assert not report.ok
    assert "unresolved_placeholder" in report.issue_codes


def test_vitrine_blocks_generic_title() -> None:
    html = _VITRINE_OK.replace(
        "<title>Aux Délices — Boulangerie Rouen</title>",
        "<title>Site web</title>",
    )
    report = analyze_vitrine_html(html)
    assert not report.ok
    assert "generic_title" in report.issue_codes


def test_vitrine_blocks_missing_h1() -> None:
    html = _VITRINE_OK.replace("<h1>", "<h2>")
    report = analyze_vitrine_html(html)
    assert not report.ok
    assert "missing_h1" in report.issue_codes


def test_vitrine_blocks_missing_contact() -> None:
    html = re.sub(r'<section id="contact"[\s\S]*</section>', "", _VITRINE_OK)
    report = analyze_vitrine_html(html)
    assert not report.ok
    assert "missing_contact" in report.issue_codes

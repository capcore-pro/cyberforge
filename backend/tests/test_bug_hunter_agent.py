"""Tests BugHunterAI — détection défauts HTML."""

from agents.bug_hunter_agent import BugHunterAgent, analyze_demo_html
from tools.standalone_demo_html import build_task_manager_standalone_html

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

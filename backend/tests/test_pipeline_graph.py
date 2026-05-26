"""Tests du routage LangGraph (BuilderAI, BugHunter → AutoFix, mode real_app)."""

from agents.bug_hunter_agent import BugHuntReport, BugIssue
from agents.pipeline_graph import (
    MAX_AUTOFIX_LOOPS,
    MAX_TESTPILOT_AUTOFIX_LOOPS,
    _inject_package_json,
    _route_after_builder,
    _route_after_bughunter,
    _route_after_testpilot,
)
from agents.testpilot_agent import TestPilotReport
from tools.codegen_service import CodeGenerateResult, GeneratedFile


def test_route_builder_fallback_to_coremind() -> None:
    assert _route_after_builder({"builder_fallback": True}) == "coremind"


def test_route_builder_success_skips_coremind() -> None:
    assert (
        _route_after_builder(
            {"builder_fallback": False, "generation": object()},
        )
        == "visionui"
    )



def test_route_ok_goes_testpilot() -> None:
    state = {
        "bug_report": BugHuntReport(ok=True, html_bytes=5000),
        "fix_loops": 0,
    }
    assert _route_after_bughunter(state) == "testpilot"


def test_route_issues_goes_autofix() -> None:
    state = {
        "bug_report": BugHuntReport(
            ok=False,
            issues=[BugIssue(code="missing_css", message="test")],
        ),
        "fix_loops": 0,
    }
    assert _route_after_bughunter(state) == "autofix"


def test_route_max_loops_goes_testpilot() -> None:
    state = {
        "bug_report": BugHuntReport(
            ok=False,
            issues=[BugIssue(code="missing_css", message="test")],
        ),
        "fix_loops": MAX_AUTOFIX_LOOPS,
    }
    assert _route_after_bughunter(state) == "testpilot"


def test_route_testpilot_ok_export() -> None:
    assert _route_after_testpilot({"testpilot_report": TestPilotReport(ok=True)}) == "export"


def test_route_testpilot_fail_to_autofix() -> None:
    assert (
        _route_after_testpilot(
            {
                "testpilot_report": TestPilotReport(ok=False),
                "testpilot_refix_loops": 1,
            }
        )
        == "autofix"
    )


def test_route_testpilot_max_refix_export() -> None:
    assert (
        _route_after_testpilot(
            {
                "testpilot_report": TestPilotReport(ok=False),
                "testpilot_refix_loops": MAX_TESTPILOT_AUTOFIX_LOOPS + 1,
            }
        )
        == "export"
    )


def _make_generation(files: list[GeneratedFile] | None = None) -> CodeGenerateResult:
    return CodeGenerateResult(
        summary="test",
        code="export default function App(){ return null; }",
        files=files or [GeneratedFile(path="src/App.tsx", content="...")],
        stack=["react"],
        model="test-model",
        provider="test",
    )


def test_inject_package_json_adds_files() -> None:
    gen = _make_generation()
    result = _inject_package_json(gen, "Mon App")
    paths = {f.path for f in result.files}
    assert "package.json" in paths
    assert "index.html" in paths
    assert "src/main.tsx" in paths


def test_inject_package_json_noop_when_present() -> None:
    existing = [
        GeneratedFile(path="src/App.tsx", content="..."),
        GeneratedFile(path="package.json", content='{"name":"x"}'),
    ]
    gen = _make_generation(existing)
    result = _inject_package_json(gen, "Mon App")
    pkg_files = [f for f in result.files if f.path == "package.json"]
    assert len(pkg_files) == 1


def test_inject_package_json_adds_react_to_stack() -> None:
    gen = _make_generation()
    result = _inject_package_json(gen, "Mon App")
    assert "react" in result.stack
    assert "typescript" in result.stack
    assert "vite" in result.stack

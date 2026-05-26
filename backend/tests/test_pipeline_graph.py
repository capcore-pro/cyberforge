"""Tests du routage LangGraph (BuilderAI, BugHunter → AutoFix)."""

from agents.bug_hunter_agent import BugHuntReport, BugIssue
from agents.pipeline_graph import (
    MAX_AUTOFIX_LOOPS,
    MAX_TESTPILOT_AUTOFIX_LOOPS,
    _route_after_builder,
    _route_after_bughunter,
    _route_after_testpilot,
)
from agents.testpilot_agent import TestPilotReport


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

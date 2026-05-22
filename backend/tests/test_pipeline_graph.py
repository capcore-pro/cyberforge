"""Tests du routage LangGraph (BugHunter → AutoFix, max 2 boucles)."""

from agents.bug_hunter_agent import BugHuntReport, BugIssue
from agents.pipeline_graph import MAX_AUTOFIX_LOOPS, _route_after_bughunter


def test_route_ok_skips_autofix() -> None:
    state = {
        "bug_report": BugHuntReport(ok=True, html_bytes=5000),
        "fix_loops": 0,
    }
    assert _route_after_bughunter(state) == "finalize"


def test_route_issues_goes_autofix() -> None:
    state = {
        "bug_report": BugHuntReport(
            ok=False,
            issues=[BugIssue(code="missing_css", message="test")],
        ),
        "fix_loops": 0,
    }
    assert _route_after_bughunter(state) == "autofix"


def test_route_max_loops_finalize() -> None:
    state = {
        "bug_report": BugHuntReport(
            ok=False,
            issues=[BugIssue(code="missing_css", message="test")],
        ),
        "fix_loops": MAX_AUTOFIX_LOOPS,
    }
    assert _route_after_bughunter(state) == "finalize"

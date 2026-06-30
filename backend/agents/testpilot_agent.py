"""
TestPilotAI — validation finale HTML/JS (rendu, liens, scripts) avant livraison.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from agents.bug_hunter_agent import BugHuntReport, BugIssue, BugHunterAgent
from agents.demo_quality import preview_html_from_generation
from tools.codegen_service import CodeGenerateResult
from tools.generation_sources import is_usable_preview_html

_JS_SYNTAX_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"console\.error\s*\(", "appel console.error dans le script"),
    (r"\bthrow\s+new\s+Error", "throw Error non géré (risque console)"),
    (r"<<<<<<<|=======|>>>>>>>", "marqueurs de conflit Git dans un script"),
    (r"undefined\s+is\s+not", "erreur runtime typique affichée dans le HTML"),
    (r"SyntaxError", "SyntaxError référencée dans le document"),
    (r"ReferenceError", "ReferenceError référencée dans le document"),
)

_BROKEN_LINK_PATTERNS: tuple[tuple[str, str], ...] = (
    (r'href\s*=\s*["\']#["\']', "lien vide href=\"#\""),
    (r'href\s*=\s*["\']\s*["\']', "lien href vide"),
    (r'javascript:\s*void\s*\(\s*0\s*\)', "lien javascript:void(0) non fonctionnel"),
)


class TestPilotIssue(BaseModel):
    code: str
    message: str
    severity: str = "error"


class TestPilotReport(BaseModel):
    """Rapport de validation TestPilotAI."""

    agent_id: str = "testpilot"
    agent_name: str = "TestPilotAI"
    ok: bool
    html_bytes: int = 0
    issues: list[TestPilotIssue] = Field(default_factory=list)
    checks_run: list[str] = Field(default_factory=list)

    @property
    def issue_codes(self) -> list[str]:
        return [i.code for i in self.issues]


class _AnchorCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []
        self.scripts: list[str] = []
        self.has_body = False
        self.has_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lower = tag.lower()
        if lower == "body":
            self.has_body = True
        attr_map = {k.lower(): (v or "") for k, v in attrs}
        if lower == "a" and "href" in attr_map:
            self.hrefs.append(attr_map["href"].strip())
        if lower == "script":
            self.scripts.append(attr_map.get("src", ""))

    def handle_data(self, data: str) -> None:
        if data.strip() and len(data.strip()) > 2:
            pass


def _extract_script_bodies(html: str) -> list[str]:
    return re.findall(r"<script[^>]*>([\s\S]*?)</script>", html, re.I)


def validate_demo_html(html: str) -> TestPilotReport:
    """Valide le HTML généré (heuristiques rendu, liens, JS)."""
    checks: list[str] = []
    issues: list[TestPilotIssue] = []
    stripped = html.strip()
    size = len(stripped.encode("utf-8"))
    checks.append("structure_html")

    if size < 400:
        issues.append(
            TestPilotIssue(
                code="render_invalid",
                message="Document trop court pour un rendu fiable.",
            )
        )

    lower = stripped.lower()
    if "<!doctype" not in lower and "<html" not in lower:
        issues.append(
            TestPilotIssue(
                code="render_invalid",
                message="DOCTYPE ou balise html manquante.",
            )
        )

    if not is_usable_preview_html(stripped):
        issues.append(
            TestPilotIssue(
                code="render_invalid",
                message="Aperçu HTML non utilisable (shell vide ou source visible).",
            )
        )

    parser = _AnchorCollector()
    try:
        parser.feed(stripped)
        checks.append("parse_dom")
    except Exception as exc:
        issues.append(
            TestPilotIssue(
                code="render_invalid",
                message=f"HTML non parseable : {exc}",
            )
        )
        parser = _AnchorCollector()

    if not parser.has_body:
        issues.append(
            TestPilotIssue(code="render_invalid", message="Balise body absente.")
        )

    checks.append("links")
    for href in parser.hrefs:
        if href in ("", "#"):
            issues.append(
                TestPilotIssue(
                    code="broken_link",
                    message=f"Lien non fonctionnel : href={href!r}",
                )
            )
            continue
        if href.startswith("#"):
            anchor = href[1:]
            if anchor and f'id="{anchor}"' not in stripped and f"id='{anchor}'" not in stripped:
                issues.append(
                    TestPilotIssue(
                        code="broken_link",
                        message=f"Ancre introuvable : {href}",
                    )
                )
            continue
        if href.startswith(("http://", "https://", "mailto:", "tel:", "/", "./", "../")):
            continue
        if href.startswith("javascript:"):
            issues.append(
                TestPilotIssue(
                    code="broken_link",
                    message=f"Lien javascript non testable : {href[:60]}",
                )
            )
            continue
        parsed = urlparse(href)
        if not parsed.scheme and not href.startswith("#"):
            issues.append(
                TestPilotIssue(
                    code="broken_link",
                    message=f"URL relative ou invalide : {href[:80]}",
                )
            )

    for pattern, msg in _BROKEN_LINK_PATTERNS:
        if re.search(pattern, stripped, re.I):
            issues.append(TestPilotIssue(code="broken_link", message=msg))

    checks.append("javascript")
    for body in _extract_script_bodies(html):
        if not body.strip():
            continue
        open_paren = body.count("(") - body.count(")")
        open_brace = body.count("{") - body.count("}")
        open_bracket = body.count("[") - body.count("]")
        if open_paren != 0 or open_brace != 0 or open_bracket != 0:
            issues.append(
                TestPilotIssue(
                    code="js_console_risk",
                    message="Script inline : parenthèses/accolades non équilibrées.",
                )
            )
        for pattern, msg in _JS_SYNTAX_PATTERNS:
            if re.search(pattern, body, re.I):
                issues.append(TestPilotIssue(code="js_console_risk", message=msg))

    for pattern, msg in _JS_SYNTAX_PATTERNS:
        if re.search(pattern, stripped, re.I):
            issues.append(
                TestPilotIssue(code="js_console_risk", message=f"Document : {msg}")
            )

    return TestPilotReport(
        ok=len(issues) == 0,
        html_bytes=size,
        issues=issues,
        checks_run=checks,
    )


def testpilot_to_bug_report(report: TestPilotReport) -> BugHuntReport:
    """Convertit un échec TestPilot en rapport BugHunter pour AutoFixAI."""
    return BugHuntReport(
        ok=False,
        html_bytes=report.html_bytes,
        issues=[
            BugIssue(code=issue.code, message=issue.message, severity=issue.severity)
            for issue in report.issues
        ],
    )


class TestPilotAgent(BaseAgent):
    """Valide le livrable HTML avant finalisation."""

    @property
    def agent_id(self) -> str:
        return "testpilot"

    @property
    def name(self) -> str:
        return "TestPilotAI"

    async def run(self, prompt: str, **kwargs: Any) -> str:
        html = str(kwargs.get("html") or prompt)
        report = self.validate_html(html)
        return report.model_dump_json()

    def validate_html(self, html: str) -> TestPilotReport:
        return validate_demo_html(html)

    def validate_generation(
        self,
        generation: CodeGenerateResult,
        *,
        title: str = "Démo",
        user_prompt: str = "",
    ) -> TestPilotReport:
        preview = preview_html_from_generation(
            generation,
            title=title,
            user_prompt=user_prompt,
        )
        html = (preview or generation.code or "").strip()
        return self.validate_html(html)

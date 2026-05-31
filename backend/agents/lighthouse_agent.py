"""
LighthouseAgent — audit qualité (Performance, SEO, Accessibilité, Bonnes pratiques).

Exécute Lighthouse via Node.js (subprocess) sur l'aperçu HTML local ou une URL live.
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from agents.bug_hunter_agent import BugHuntReport, BugIssue
from agents.playwright_agent import _start_preview_server, _stop_preview_server
from config import Settings, get_settings

logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
PASS_THRESHOLD = 70


class LighthouseReport(BaseModel):
    """Rapport Lighthouse — 4 scores + score global."""

    agent_id: str = "lighthouse"
    agent_name: str = "Lighthouse"
    performance: int = 0
    seo: int = 0
    accessibility: int = 0
    best_practices: int = 0
    score_global: int = 0
    ok: bool = False
    recommendations: list[str] = Field(default_factory=list)
    target_url: str = ""
    skipped: bool = False
    skip_reason: str | None = None
    full_report: dict[str, Any] | None = Field(
        default=None,
        description="Rapport JSON Lighthouse complet (audits, categories).",
    )

    @property
    def issue_messages(self) -> list[str]:
        return list(self.recommendations)


def _lighthouse_cli_command(url: str, output_path: Path) -> list[str]:
    cli = _BACKEND_ROOT / "node_modules" / "lighthouse" / "cli" / "index.js"
    if cli.is_file():
        return [
            "node",
            str(cli),
            url,
            "--output=json",
            f"--output-path={output_path}",
            "--quiet",
            "--chrome-flags=--headless --no-sandbox --disable-gpu",
            "--only-categories=performance,seo,accessibility,best-practices",
        ]
    return [
        "npx",
        "--yes",
        "lighthouse",
        url,
        "--output=json",
        f"--output-path={output_path}",
        "--quiet",
        "--chrome-flags=--headless --no-sandbox --disable-gpu",
        "--only-categories=performance,seo,accessibility,best-practices",
    ]


def _category_score(categories: dict[str, Any], key: str) -> int:
    raw = categories.get(key, {})
    if not isinstance(raw, dict):
        return 0
    score = raw.get("score")
    if score is None:
        return 0
    try:
        return max(0, min(100, round(float(score) * 100)))
    except (TypeError, ValueError):
        return 0


def _build_recommendations(lhr: dict[str, Any], *, limit: int = 12) -> list[str]:
    audits = lhr.get("audits")
    if not isinstance(audits, dict):
        return []
    recs: list[tuple[float, str]] = []
    for audit_id, audit in audits.items():
        if not isinstance(audit, dict):
            continue
        score = audit.get("score")
        if score is None:
            continue
        try:
            score_f = float(score)
        except (TypeError, ValueError):
            continue
        if score_f >= 0.9:
            continue
        title = str(audit.get("title") or audit_id).strip()
        display = audit.get("displayValue")
        if display:
            recs.append((score_f, f"{title} — {display}"))
        else:
            recs.append((score_f, title))
    recs.sort(key=lambda item: item[0])
    return [text for _, text in recs[:limit]]


def _parse_lighthouse_json(
    lhr: dict[str, Any],
    *,
    target_url: str,
    pass_threshold: int,
) -> LighthouseReport:
    categories = lhr.get("categories") if isinstance(lhr.get("categories"), dict) else {}
    performance = _category_score(categories, "performance")
    seo = _category_score(categories, "seo")
    accessibility = _category_score(categories, "accessibility")
    best_practices = _category_score(categories, "best-practices")
    scores = [performance, seo, accessibility, best_practices]
    score_global = round(sum(scores) / len(scores)) if scores else 0
    recommendations = _build_recommendations(lhr)
    if score_global < pass_threshold and not recommendations:
        recommendations = [
            f"Score global {score_global}/100 — améliorer Performance ({performance}), "
            f"SEO ({seo}), Accessibilité ({accessibility}), Bonnes pratiques ({best_practices}).",
        ]
    return LighthouseReport(
        performance=performance,
        seo=seo,
        accessibility=accessibility,
        best_practices=best_practices,
        score_global=score_global,
        ok=score_global >= pass_threshold,
        recommendations=recommendations,
        target_url=target_url,
        full_report=lhr,
    )


def lighthouse_to_bug_report(report: LighthouseReport) -> BugHuntReport:
    """Convertit un échec Lighthouse en rapport BugHunter pour AutoFixAI."""
    issues = [
        BugIssue(
            code="lighthouse_recommendation",
            message=item,
            severity="warning" if report.score_global >= 50 else "error",
        )
        for item in report.recommendations
    ]
    if not issues:
        issues = [
            BugIssue(
                code="lighthouse_low_score",
                message=f"Score Lighthouse global {report.score_global}/100",
                severity="error",
            )
        ]
    return BugHuntReport(ok=False, html_bytes=0, issues=issues)


def _run_lighthouse_sync(url: str, timeout_seconds: float) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="cf-lighthouse-") as tmp:
        out_path = Path(tmp) / "report.json"
        cmd = _lighthouse_cli_command(url, out_path)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=str(_BACKEND_ROOT),
        )
        if result.returncode != 0 and not out_path.is_file():
            stderr = (result.stderr or result.stdout or "").strip()[:500]
            raise RuntimeError(stderr or f"Lighthouse exit code {result.returncode}")
        if not out_path.is_file():
            raise RuntimeError("Rapport Lighthouse JSON introuvable")
        return json.loads(out_path.read_text(encoding="utf-8"))


class LighthouseAgent(BaseAgent):
    """Audit Lighthouse (subprocess Node.js) sur preview ou URL déployée."""

    @property
    def agent_id(self) -> str:
        return "lighthouse"

    @property
    def name(self) -> str:
        return "Lighthouse"

    def is_available(self) -> bool:
        cli = _BACKEND_ROOT / "node_modules" / "lighthouse" / "cli" / "index.js"
        return cli.is_file()

    async def run(self, prompt: str, **kwargs: Any) -> str:
        html = str(kwargs.get("html") or prompt)
        url = kwargs.get("url")
        report = await self.audit_site(html=html, base_url=url)
        return report.model_dump_json()

    async def audit_site(
        self,
        *,
        html: str | None = None,
        base_url: str | None = None,
        settings: Settings | None = None,
    ) -> LighthouseReport:
        resolved = settings or self._settings
        threshold = resolved.lighthouse_pass_threshold

        if not resolved.lighthouse_enabled:
            return LighthouseReport(
                score_global=100,
                performance=100,
                seo=100,
                accessibility=100,
                best_practices=100,
                ok=True,
                skipped=True,
                skip_reason="Lighthouse désactivé",
            )

        server = None
        target = (base_url or "").strip()
        preview_html = (html or "").strip()

        try:
            if not target:
                if len(preview_html) < 200:
                    return LighthouseReport(
                        score_global=100,
                        performance=100,
                        seo=100,
                        accessibility=100,
                        best_practices=100,
                        ok=True,
                        skipped=True,
                        skip_reason="Aucun HTML preview pour Lighthouse",
                    )
                server, target = _start_preview_server(preview_html)

            timeout = resolved.lighthouse_timeout_seconds + 30
            lhr = await asyncio.wait_for(
                asyncio.to_thread(
                    _run_lighthouse_sync,
                    target,
                    resolved.lighthouse_timeout_seconds,
                ),
                timeout=timeout,
            )
            return _parse_lighthouse_json(
                lhr,
                target_url=target,
                pass_threshold=threshold,
            )
        except asyncio.TimeoutError:
            return LighthouseReport(
                target_url=target,
                recommendations=["timeout: audit Lighthouse dépassé"],
                score_global=0,
                ok=False,
            )
        except FileNotFoundError:
            return LighthouseReport(
                score_global=100,
                performance=100,
                seo=100,
                accessibility=100,
                best_practices=100,
                ok=True,
                skipped=True,
                skip_reason="Node.js ou Lighthouse non installé (npm install dans backend/)",
            )
        except Exception as exc:
            logger.exception("LighthouseAgent")
            msg = str(exc).strip()[:400]
            if "Cannot find module" in msg or "lighthouse" in msg.lower():
                return LighthouseReport(
                    score_global=100,
                    performance=100,
                    seo=100,
                    accessibility=100,
                    best_practices=100,
                    ok=True,
                    skipped=True,
                    skip_reason="Lighthouse non installé (npm install --prefix backend/node_modules)",
                )
            return LighthouseReport(
                target_url=target,
                recommendations=[f"erreur Lighthouse: {msg}"],
                score_global=0,
                ok=False,
            )
        finally:
            _stop_preview_server(server)

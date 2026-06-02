"""
PlaywrightAgent — tests E2E headless (Chromium) sur l'aperçu HTML avant export.

Sert le HTML en local si aucune URL de production n'est disponible.
"""

from __future__ import annotations

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import logging
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import urljoin, urlparse

from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from agents.bug_hunter_agent import BugHuntReport, BugIssue
from config import Settings, get_settings

logger = logging.getLogger(__name__)

PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.async_api import async_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    async_playwright = None  # type: ignore[assignment,misc]

PASS_THRESHOLD = 70


class PlaywrightReport(BaseModel):
    """Rapport de tests Playwright — score 0-100."""

    agent_id: str = "playwright"
    agent_name: str = "Playwright"
    passed: list[str] = Field(default_factory=list)
    failed: list[str] = Field(default_factory=list)
    score: int = 0
    ok: bool = False
    target_url: str = ""
    skipped: bool = False
    skip_reason: str | None = None

    @property
    def issue_messages(self) -> list[str]:
        return list(self.failed)


class _PreviewHandler(BaseHTTPRequestHandler):
    html: str = ""

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            body = self.html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _start_preview_server(html: str) -> tuple[HTTPServer, str]:
    port = _free_port()
    handler = type("Handler", (_PreviewHandler,), {})
    handler.html = html
    server = HTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{port}/"


def _stop_preview_server(server: HTTPServer | None) -> None:
    if server is None:
        return
    try:
        server.shutdown()
    except Exception:
        pass


def playwright_to_bug_report(report: PlaywrightReport) -> BugHuntReport:
    """Convertit un échec Playwright en rapport BugHunter pour AutoFixAI."""
    issues = [
        BugIssue(
            code="playwright_failed",
            message=item,
            severity="error",
        )
        for item in report.failed
    ]
    return BugHuntReport(ok=False, html_bytes=0, issues=issues)


class PlaywrightAgent(BaseAgent):
    """Tests automatiques Chromium headless sur le site (preview ou URL live)."""

    @property
    def agent_id(self) -> str:
        return "playwright"

    @property
    def name(self) -> str:
        return "Playwright"

    def is_available(self) -> bool:
        return PLAYWRIGHT_AVAILABLE

    async def run(self, prompt: str, **kwargs: Any) -> str:
        html = str(kwargs.get("html") or prompt)
        url = kwargs.get("url")
        report = await self.test_site(html=html, base_url=url)
        return report.model_dump_json()

    async def test_site(
        self,
        *,
        html: str | None = None,
        base_url: str | None = None,
        settings: Settings | None = None,
        vitrine_mode: bool = False,
        prefer_local_preview: bool = False,
    ) -> PlaywrightReport:
        resolved = settings or self._settings
        threshold = resolved.playwright_pass_threshold

        if not resolved.playwright_enabled:
            return PlaywrightReport(
                score=100,
                ok=True,
                skipped=True,
                skip_reason="Playwright désactivé",
                passed=["playwright_disabled"],
            )

        if not PLAYWRIGHT_AVAILABLE:
            return PlaywrightReport(
                score=100,
                ok=True,
                skipped=True,
                skip_reason="playwright non installé (pip install playwright)",
                passed=["playwright_unavailable"],
            )

        server: HTTPServer | None = None
        target = (base_url or "").strip()
        preview_html = (html or "").strip()

        if prefer_local_preview or vitrine_mode:
            target = ""

        try:
            if not target:
                if len(preview_html) < 80:
                    return PlaywrightReport(
                        score=100,
                        ok=True,
                        skipped=True,
                        skip_reason="Aucun HTML preview pour les tests Playwright",
                        passed=["playwright_skipped_no_html"],
                    )
                from tools.vitrine_html_normalize import extract_unlocked_demo_html

                preview_html = extract_unlocked_demo_html(preview_html)
                server, target = _start_preview_server(preview_html)
                logger.info(
                    "[Playwright] serveur local | url=%s | html_bytes=%d | vitrine=%s",
                    target,
                    len(preview_html.encode("utf-8")),
                    vitrine_mode,
                )

            timeout_ms = int(resolved.playwright_timeout_seconds * 1000)
            runner = (
                _run_vitrine_playwright_checks
                if vitrine_mode
                else _run_playwright_checks
            )
            report = await asyncio.wait_for(
                runner(
                    target,
                    timeout_ms=timeout_ms,
                    pass_threshold=threshold,
                ),
                timeout=resolved.playwright_timeout_seconds + 15,
            )
            return report
        except asyncio.TimeoutError:
            return PlaywrightReport(
                target_url=target,
                failed=["timeout: tests Playwright dépassés"],
                score=0,
                ok=False,
            )
        except Exception as exc:
            logger.exception("PlaywrightAgent")
            return PlaywrightReport(
                target_url=target,
                failed=[f"erreur Playwright: {exc}"],
                score=0,
                ok=False,
            )
        finally:
            _stop_preview_server(server)


async def _run_vitrine_playwright_checks(
    base_url: str,
    *,
    timeout_ms: int,
    pass_threshold: int = PASS_THRESHOLD,
) -> PlaywrightReport:
    """Tests minimaux pour vitrine HTML statique (serveur local)."""
    assert async_playwright is not None
    passed: list[str] = []
    failed: list[str] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            response = await page.goto(
                base_url, wait_until="domcontentloaded", timeout=timeout_ms
            )
            status = response.status if response else 0
            if status == 200:
                passed.append("page_load_200")
            else:
                failed.append(f"page_load: status HTTP {status}")

            h1_count = await page.locator("h1").count()
            h1_visible = await page.locator("h1").first.is_visible() if h1_count else False
            if h1_count > 0 and h1_visible:
                passed.append("vitrine_h1_visible")
            else:
                failed.append("vitrine_h1: titre principal absent ou masqué")

            if await page.locator("#contact, #cf-contact-form, form").count() > 0:
                passed.append("vitrine_contact")
            else:
                failed.append("vitrine_contact: section ou formulaire contact manquant")

            title_ok = await page.title()
            if title_ok and len(title_ok.strip()) >= 3:
                passed.append("vitrine_title")
            else:
                failed.append("vitrine_title: balise title vide")

            body_h = await page.evaluate("() => document.body?.scrollHeight || 0")
            if body_h > 80:
                passed.append("vitrine_body_content")
            else:
                failed.append("vitrine_body: contenu trop court")
        finally:
            await browser.close()

    total = 5
    score = min(100, round(len(passed) / total * 100))
    return PlaywrightReport(
        passed=passed,
        failed=failed,
        score=score,
        ok=score >= pass_threshold,
        target_url=base_url,
    )


async def _run_playwright_checks(
    base_url: str,
    *,
    timeout_ms: int,
    pass_threshold: int = PASS_THRESHOLD,
) -> PlaywrightReport:
    assert async_playwright is not None
    passed: list[str] = []
    failed: list[str] = []
    parsed_base = urlparse(base_url)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            context = await browser.new_context()
            page = await context.new_page()

            # 1. Chargement page principale (200)
            response = await page.goto(base_url, wait_until="domcontentloaded", timeout=timeout_ms)
            status = response.status if response else 0
            if status == 200:
                passed.append("page_load_200")
            else:
                failed.append(f"page_load: status HTTP {status}")

            # 2. Liens internes (pas de 404)
            hrefs: list[str] = await page.eval_on_selector_all(
                "a[href]",
                "els => els.map(a => a.getAttribute('href')).filter(Boolean)",
            )
            internal = [
                h
                for h in hrefs
                if h.startswith("/") or h.startswith("#") or urlparse(h).netloc == parsed_base.netloc
            ][:20]
            broken_links: list[str] = []
            for href in internal:
                if href.startswith("#"):
                    continue
                full = urljoin(base_url, href)
                try:
                    link_resp = await page.request.get(full, timeout=timeout_ms)
                    if link_resp.status >= 400:
                        broken_links.append(f"{href} → {link_resp.status}")
                except Exception as exc:
                    broken_links.append(f"{href} → {exc}")
            if not internal:
                passed.append("internal_links: aucun lien interne")
            elif not broken_links:
                passed.append(f"internal_links: {len(internal)} lien(s) OK")
            else:
                failed.append(f"internal_links: {broken_links[0]}")

            # 3. Formulaires présents et soumettables
            form_count = await page.locator("form").count()
            if form_count == 0:
                passed.append("forms: aucun formulaire (N/A)")
            else:
                has_inputs = await page.locator("form input, form textarea, form select").count()
                has_submit = await page.locator(
                    "form button, form input[type=submit], form [type=submit]"
                ).count()
                if has_inputs > 0 and has_submit > 0:
                    passed.append(f"forms: {form_count} formulaire(s) soumettable(s)")
                else:
                    failed.append("forms: formulaire sans champs ou bouton submit")

            # 4. Boutons CTA cliquables
            cta_selector = (
                "button, a.btn, a.button, [class*='cta'], [class*='btn-primary'], "
                "input[type=button], input[type=submit]"
            )
            cta_count = await page.locator(cta_selector).count()
            if cta_count == 0:
                passed.append("cta: aucun CTA détecté (N/A)")
            else:
                try:
                    first = page.locator(cta_selector).first
                    await first.click(timeout=3000)
                    passed.append(f"cta: {cta_count} CTA, premier cliquable")
                except Exception as exc:
                    failed.append(f"cta: clic échoué ({exc})")

            # 5. Responsive mobile + desktop
            for label, width, height in (("mobile_375", 375, 812), ("desktop_1280", 1280, 720)):
                await page.set_viewport_size({"width": width, "height": height})
                await page.wait_for_timeout(200)
                visible = await page.locator("body").is_visible()
                body_h = await page.evaluate("() => document.body?.scrollHeight || 0")
                if visible and body_h > 50:
                    passed.append(f"responsive_{label}")
                else:
                    failed.append(f"responsive_{label}: contenu non visible")

            # 6. Images chargées
            img_stats = await page.evaluate(
                """() => {
                  const imgs = Array.from(document.querySelectorAll('img'));
                  if (!imgs.length) return { total: 0, broken: 0 };
                  let broken = 0;
                  for (const img of imgs) {
                    if (!img.complete || img.naturalWidth === 0) broken += 1;
                  }
                  return { total: imgs.length, broken };
                }"""
            )
            total_imgs = int(img_stats.get("total", 0))
            broken_imgs = int(img_stats.get("broken", 0))
            if total_imgs == 0:
                passed.append("images: aucune image (N/A)")
            elif broken_imgs == 0:
                passed.append(f"images: {total_imgs} image(s) OK")
            else:
                failed.append(f"images: {broken_imgs}/{total_imgs} image(s) cassée(s)")

        finally:
            await browser.close()

    total_cats = 7
    cat_passed = sum(
        [
            1 if "page_load_200" in passed else 0,
            1 if any("internal_links" in p for p in passed) else 0,
            1 if any("forms" in p for p in passed) else 0,
            1 if any("cta" in p for p in passed) else 0,
            1 if any("responsive_mobile_375" in p for p in passed) else 0,
            1 if any("responsive_desktop_1280" in p for p in passed) else 0,
            1 if any("images" in p for p in passed) else 0,
        ]
    )
    score = min(100, round(cat_passed / total_cats * 100))

    return PlaywrightReport(
        passed=passed,
        failed=failed,
        score=score,
        ok=score >= pass_threshold,
        target_url=base_url,
    )

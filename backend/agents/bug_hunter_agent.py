"""
BugHunterAI — analyse heuristique du HTML généré pour les démos client.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from agents.demo_quality import preview_html_from_generation
from tools.codegen_service import CodeGenerateResult
from tools.generation_sources import is_usable_preview_html

_REACT_SOURCE_EXT = re.compile(r"\.(tsx|jsx)$", re.I)


class BugIssue(BaseModel):
    """Problème détecté dans le HTML livrable."""

    code: str
    message: str
    severity: str = "error"


class BugHuntReport(BaseModel):
    """Rapport d'analyse BugHunterAI."""

    agent_id: str = "bughunter"
    agent_name: str = "BugHunterAI"
    ok: bool
    html_bytes: int = 0
    issues: list[BugIssue] = Field(default_factory=list)

    @property
    def issue_codes(self) -> list[str]:
        return [i.code for i in self.issues]


_VISIBLE_SOURCE_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bexport\s+default\b", "export default visible"),
    (r"\bimport\s+[\w{].*from\s+['\"]react", "import React visible"),
    (r"\buseState\s*\(", "hook React useState visible"),
    (r"\buseEffect\s*\(", "hook React useEffect visible"),
    (r"\bclassName\s*=", "attribut JSX className visible"),
    (r"```(?:tsx|jsx|typescript)", "bloc markdown code visible"),
    (r"src/App\.tsx", "référence fichier TSX visible"),
)

_JS_BROKEN_PATTERNS: tuple[tuple[str, str], ...] = (
    (r'id=["\']cf-demo-root["\']>\s*\\n', "contenu JSX échappé dans le DOM"),
    (r'class=\\"', "classes Tailwind échappées (JSON/HTML cassé)"),
    (r"<script[^>]*>[\s\S]*?<<<<<<<", "conflit git dans un script"),
)


def _strip_scripts_and_styles(html: str) -> str:
    """Corps approximatif hors scripts/styles pour détecter du code source affiché."""
    text = re.sub(r"<script[\s\S]*?</script>", "", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.I)
    return text


def _count_style_rules(html: str) -> int:
    blocks = re.findall(r"<style[^>]*>([\s\S]*?)</style>", html, re.I)
    total = 0
    for block in blocks:
        total += len(re.findall(r"[.#\w][\w-]*\s*\{", block))
    total += len(re.findall(r'\sstyle\s*=\s*["\']', html, re.I))
    return total


def _empty_shell_ids(html: str) -> list[str]:
    empty: list[str] = []
    for element_id, label in (
        ("cf-login-screen", "écran de connexion"),
        ("cf-demo-content", "contenu démo"),
        ("cf-demo-root", "racine démo statique"),
    ):
        match = re.search(
            rf'<[^>]+id=["\']{element_id}["\'][^>]*>([\s\S]*?)</',
            html,
            re.I,
        )
        if not match:
            continue
        inner = re.sub(r"<[^>]+>", "", match.group(1)).strip()
        if len(inner) < 12:
            empty.append(label)
    return empty


def analyze_demo_html(html: str) -> BugHuntReport:
    """Analyse le HTML et retourne un rapport (sans appel LLM)."""
    issues: list[BugIssue] = []
    stripped = html.strip()
    size = len(stripped.encode("utf-8"))

    if size < 400:
        issues.append(
            BugIssue(
                code="render_error",
                message="Document HTML trop court ou incomplet.",
            )
        )

    lower = stripped.lower()
    if "<!doctype" not in lower and "<html" not in lower:
        issues.append(
            BugIssue(
                code="render_error",
                message="Structure HTML invalide (DOCTYPE/html manquant).",
            )
        )

    if not is_usable_preview_html(stripped):
        issues.append(
            BugIssue(
                code="render_error",
                message="Aperçu non exploitable (corps vide, JSON échappé ou DOM cassé).",
            )
        )

    visible_body = _strip_scripts_and_styles(stripped)
    for pattern, desc in _VISIBLE_SOURCE_PATTERNS:
        if re.search(pattern, visible_body, re.I):
            issues.append(
                BugIssue(
                    code="visible_source",
                    message=f"Code source probablement visible : {desc}.",
                )
            )

    for pattern, desc in _JS_BROKEN_PATTERNS:
        if re.search(pattern, stripped, re.I):
            issues.append(
                BugIssue(
                    code="broken_js",
                    message=f"JavaScript / rendu cassé : {desc}.",
                )
            )

    if _count_style_rules(stripped) < 2:
        issues.append(
            BugIssue(
                code="missing_css",
                message="CSS insuffisant (peu ou pas de règles <style> / inline).",
            )
        )

    open_scripts = len(re.findall(r"<script\b", stripped, re.I))
    close_scripts = len(re.findall(r"</script>", stripped, re.I))
    if open_scripts != close_scripts:
        issues.append(
            BugIssue(
                code="broken_js",
                message="Balises <script> non équilibrées.",
            )
        )

    for label in _empty_shell_ids(stripped):
        issues.append(
            BugIssue(
                code="empty_elements",
                message=f"Élément vide ou quasi vide : {label}.",
            )
        )

    if re.search(
        r"Ouvrez le code source pour le détail|Structure détectée",
        stripped,
        re.I,
    ):
        issues.append(
            BugIssue(
                code="render_error",
                message="Maquette de repli affichant du texte technique au lieu d'une UI.",
            )
        )

    return BugHuntReport(
        ok=len(issues) == 0,
        html_bytes=size,
        issues=issues,
    )


class BugHunterAgent(BaseAgent):
    """Détecte les défauts du HTML livrable avant publication."""

    @property
    def agent_id(self) -> str:
        return "bughunter"

    @property
    def name(self) -> str:
        return "BugHunterAI"

    def analyze_html(self, html: str) -> BugHuntReport:
        return analyze_demo_html(html)

    def _generation_file_issues(
        self,
        generation: CodeGenerateResult,
    ) -> list[BugIssue]:
        """Détecte les livrables React/TSX (non HTML vanilla) avant analyse DOM."""
        issues: list[BugIssue] = []
        for file in generation.files:
            path = (file.path or "").strip()
            if _REACT_SOURCE_EXT.search(path):
                issues.append(
                    BugIssue(
                        code="visible_source",
                        message=(
                            f"Livrable React/JSX ({path}) — HTML vanilla index.html requis."
                        ),
                    )
                )
        code = (generation.code or "").strip()
        lower = code.lower()
        is_html_doc = lower.startswith("<!") or "<html" in lower[:800]
        if not is_html_doc and re.search(
            r"\b(import\s+|export\s+default|useState\s*\()",
            code,
        ):
            issues.append(
                BugIssue(
                    code="visible_source",
                    message="Le champ code contient du React/TSX, pas un document HTML.",
                )
            )
        return issues

    def analyze_generation(
        self,
        generation: CodeGenerateResult,
        *,
        title: str = "Démo CyberForge",
    ) -> BugHuntReport:
        file_issues = self._generation_file_issues(generation)
        html = preview_html_from_generation(generation, title=title)
        html_report = self.analyze_html(html)
        if not file_issues:
            return html_report
        merged = list(html_report.issues) + file_issues
        return BugHuntReport(
            ok=False,
            html_bytes=html_report.html_bytes,
            issues=merged,
        )

    async def run(self, prompt: str, **kwargs: Any) -> str:
        html = kwargs.get("html")
        if not isinstance(html, str):
            raise ValueError("BugHunterAI attend le paramètre html=...")
        return self.analyze_html(html).model_dump_json()

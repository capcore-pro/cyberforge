"""
BugHunterAI ??? analyse heuristique du HTML g??n??r?? pour les d??mos client.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from agents.architect_agent import ArchitectPlan
from agents.base_agent import BaseAgent
from agents.demo_quality import preview_html_from_generation
from agents.research_agent import ResearchBrief
from tools.client_content_profile import (
    CLIENT_LITERAL_ISSUE_CODES,
    ClientContentProfile,
    build_client_content_profile,
    repair_client_literals_in_html,
    validate_client_literals,
)
from tools.vitrine_html_enhance import enhance_builder_vitrine_html
from tools.codegen_service import CodeGenerateResult
from tools.generation_sources import is_usable_preview_html
from tools.vitrine_html_enhance import (
    find_forbidden_placeholder_issues,
    is_template_first_html_plan,
    is_vitrine_html_plan,
)

_REACT_SOURCE_EXT = re.compile(r"\.(tsx|jsx)$", re.I)

# Vitrine HTML ??? seules validations bloquantes (AutoFix max 2, puis livraison avec alertes).
VITRINE_BLOCKING_ISSUE_CODES: frozenset[str] = frozenset(
    {
        "unresolved_placeholder",
        "missing_title",
        "generic_title",
        "missing_h1",
        "missing_contact",
        "visible_source",  # livrable React/TSX au lieu d'index.html
    }
)

_GENERIC_PAGE_TITLES: frozenset[str] = frozenset(
    {
        "site web",
        "my app",
        "d??mo cyberforge",
        "demo cyberforge",
        "site vitrine",
        "untitled",
        "welcome",
        "homepage",
        "your site",
        "votre site",
        "new site",
        "document",
        "page title",
        "home",
    }
)


class BugIssue(BaseModel):
    """Probl??me d??tect?? dans le HTML livrable."""

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
    (r"src/App\.tsx", "r??f??rence fichier TSX visible"),
)

_JS_BROKEN_PATTERNS: tuple[tuple[str, str], ...] = (
    (r'id=["\']cf-demo-root["\']>\s*\\n', "contenu JSX ??chapp?? dans le DOM"),
    (r'class=\\"', "classes Tailwind ??chapp??es (JSON/HTML cass??)"),
    (r"<script[^>]*>[\s\S]*?<<<<<<<", "conflit git dans un script"),
)

_FORBIDDEN_VISIBLE_RE = re.compile(
    r"lorem\s+ipsum|\blorem\b|"
    r"votre\s+texte\s+ici|your\s+text\s+here|"
    r"example\s+corp|entreprise\s+xyz",
    re.IGNORECASE,
)


def _strip_scripts_and_styles(html: str) -> str:
    """Corps approximatif hors scripts/styles pour d??tecter du code source affich??."""
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
        ("cf-login-screen", "??cran de connexion"),
        ("cf-demo-content", "contenu d??mo"),
        ("cf-demo-root", "racine d??mo statique"),
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


def client_literal_issues_only(issue_codes: list[str]) -> bool:
    if not issue_codes:
        return False
    return set(issue_codes).issubset(CLIENT_LITERAL_ISSUE_CODES)


def vitrine_blocking_issues_only(issue_codes: list[str]) -> bool:
    """True si aucun code hors liste bloquante vitrine (alertes Playwright/Lighthouse exclues)."""
    if not issue_codes:
        return True
    return set(issue_codes).issubset(VITRINE_BLOCKING_ISSUE_CODES)


def has_vitrine_blocking_issues(report: BugHuntReport) -> bool:
    return bool(
        VITRINE_BLOCKING_ISSUE_CODES.intersection(report.issue_codes)
    )


def _strip_scripts_styles(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", "", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.I)
    return text


def _extract_page_title(html: str) -> str:
    match = re.search(r"<title[^>]*>([^<]*)</title>", html, re.I)
    return (match.group(1) if match else "").strip()


def _is_generic_page_title(title: str) -> bool:
    normalized = re.sub(r"\s+", " ", title.strip().lower())
    if not normalized:
        return True
    if normalized in _GENERIC_PAGE_TITLES:
        return True
    if len(normalized) < 4:
        return True
    return False


def _has_contact_section_or_form(html: str) -> bool:
    low = html.lower()
    if 'id="contact"' in low or "id='contact'" in low:
        return True
    if "cf-contact-form" in low:
        return True
    if re.search(r"<form\b", html, re.I) and re.search(
        r'type\s*=\s*["\']email["\']|name\s*=\s*["\']email["\']',
        html,
        re.I,
    ):
        return True
    if re.search(
        r'<section[^>]+(?:id|class)\s*=\s*["\'][^"\']*contact',
        html,
        re.I,
    ):
        return True
    return False


def repair_generation_client_literals(
    generation: CodeGenerateResult,
    profile: ClientContentProfile,
    *,
    title: str,
    research_brief: ResearchBrief | Any | None = None,
    architect_plan: ArchitectPlan | None = None,
    user_prompt: str = "",
    settings: Any = None,
) -> tuple[CodeGenerateResult, BugHuntReport]:
    """Injecte l'identit?? client dans le HTML existant puis revalide."""
    from agents.demo_quality import code_result_from_html

    if settings is None:
        from config import get_settings

        settings = get_settings()
    hunter = BugHunterAgent(settings)
    html = preview_html_from_generation(
        generation,
        title=title,
        user_prompt=user_prompt,
    )
    if architect_plan and is_vitrine_html_plan(architect_plan):
        html = enhance_builder_vitrine_html(
            html,
            plan=architect_plan,
            research_brief=research_brief,
            user_prompt=user_prompt,
        )
    fixed = repair_client_literals_in_html(html, profile, user_prompt=user_prompt)
    patched = code_result_from_html(
        fixed,
        summary=generation.summary,
        model=generation.model,
        provider=generation.provider,
    )
    report = hunter.analyze_generation(
        patched,
        title=title,
        research_brief=research_brief,
        architect_plan=architect_plan,
        user_prompt=user_prompt,
    )
    return patched, report


def analyze_vitrine_html(
    html: str,
    *,
    client_profile: ClientContentProfile | None = None,
) -> BugHuntReport:
    """
    Validation vitrine ??? 4 r??gles bloquantes uniquement :
    placeholders {{ }}, titre non g??n??rique, <h1>, contact/formulaire.
    """
    _ = client_profile  # r??serv?? ??? r??paration identit?? en amont (AutoFix)
    issues: list[BugIssue] = []
    stripped = html.strip()
    size = len(stripped.encode("utf-8"))

    visible = _strip_scripts_styles(stripped)
    if "{{" in visible:
        issues.append(
            BugIssue(
                code="unresolved_placeholder",
                message="Placeholder {{???}} non remplac?? dans le HTML.",
            )
        )

    title = _extract_page_title(stripped)
    if not title:
        issues.append(
            BugIssue(
                code="missing_title",
                message="Balise <title> manquante ou vide.",
            )
        )
    elif _is_generic_page_title(title):
        issues.append(
            BugIssue(
                code="generic_title",
                message=f"Titre g??n??rique interdit : ?? {title[:80]} ??.",
            )
        )

    if not re.search(r"<h1\b", stripped, re.I):
        issues.append(
            BugIssue(
                code="missing_h1",
                message="Balise <h1> manquante.",
            )
        )

    if not _has_contact_section_or_form(stripped):
        issues.append(
            BugIssue(
                code="missing_contact",
                message="Section contact ou formulaire manquant.",
            )
        )

    return BugHuntReport(
        ok=len(issues) == 0,
        html_bytes=size,
        issues=issues,
    )


def analyze_demo_html(
    html: str,
    *,
    client_profile: ClientContentProfile | None = None,
) -> BugHuntReport:
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
                message="Aper??u non exploitable (corps vide, JSON ??chapp?? ou DOM cass??).",
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
                    message=f"JavaScript / rendu cass?? : {desc}.",
                )
            )

    if _count_style_rules(stripped) < 2:
        issues.append(
            BugIssue(
                code="missing_css",
                message="CSS insuffisant (peu ou pas de r??gles <style> / inline).",
            )
        )

    open_scripts = len(re.findall(r"<script\b", stripped, re.I))
    close_scripts = len(re.findall(r"</script>", stripped, re.I))
    if open_scripts != close_scripts:
        issues.append(
            BugIssue(
                code="broken_js",
                message="Balises <script> non ??quilibr??es.",
            )
        )

    for label in _empty_shell_ids(stripped):
        issues.append(
            BugIssue(
                code="empty_elements",
                message=f"??l??ment vide ou quasi vide : {label}.",
            )
        )

    if re.search(
        r"Ouvrez le code source pour le d??tail|Structure d??tect??e",
        stripped,
        re.I,
    ):
        issues.append(
            BugIssue(
                code="render_error",
                message="Maquette de repli affichant du texte technique au lieu d'une UI.",
            )
        )

    for code, message in find_forbidden_placeholder_issues(
        stripped,
        client_profile=client_profile,
    ):
        issues.append(BugIssue(code=code, message=message))

    return BugHuntReport(
        ok=len(issues) == 0,
        html_bytes=size,
        issues=issues,
    )


class BugHunterAgent(BaseAgent):
    """D??tecte les d??fauts du HTML livrable avant publication."""

    @property
    def agent_id(self) -> str:
        return "bughunter"

    @property
    def name(self) -> str:
        return "BugHunterAI"

    def analyze_html(
        self,
        html: str,
        *,
        client_profile: ClientContentProfile | None = None,
    ) -> BugHuntReport:
        return analyze_demo_html(html, client_profile=client_profile)

    def _generation_file_issues(
        self,
        generation: CodeGenerateResult,
    ) -> list[BugIssue]:
        """D??tecte les livrables React/TSX (non HTML vanilla) avant analyse DOM."""
        issues: list[BugIssue] = []
        for file in generation.files:
            path = (file.path or "").strip()
            if _REACT_SOURCE_EXT.search(path):
                issues.append(
                    BugIssue(
                        code="visible_source",
                        message=(
                            f"Livrable React/JSX ({path}) ??? HTML vanilla index.html requis."
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
        title: str = "D??mo CyberForge",
        research_brief: ResearchBrief | None = None,
        architect_plan: ArchitectPlan | None = None,
        user_prompt: str = "",
    ) -> BugHuntReport:
        file_issues = self._generation_file_issues(generation)
        html = preview_html_from_generation(generation, title=title)
        profile: ClientContentProfile | None = None
        if architect_plan and is_template_first_html_plan(architect_plan):
            profile = build_client_content_profile(
                user_prompt=user_prompt,
                research_brief=research_brief,
                plan=architect_plan,
            )
            if not profile.company_name:
                profile = None
        if architect_plan and is_template_first_html_plan(architect_plan):
            html_report = analyze_vitrine_html(html, client_profile=profile)
        else:
            html_report = self.analyze_html(html, client_profile=profile)
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
            raise ValueError("BugHunterAI attend le param??tre html=...")
        return self.analyze_html(html).model_dump_json()

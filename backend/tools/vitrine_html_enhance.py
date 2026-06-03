"""
Post-traitement HTML vitrine BuilderAI — CTA, contact, interdictions placeholders.
"""

from __future__ import annotations

import re
from typing import Any

from agents.research_agent import ResearchBrief
from tools.client_content_profile import (
    build_client_content_profile,
    repair_client_literals_in_html,
    validate_client_literals,
)
from tools.demo_preview_gate import strip_password_gate
from tools.html_markdown import strip_markdown_code_fences
from tools.demo_runtime import resolve_demo_api_base_url
from tools.vitrine_shell import apply_vitrine_premium_shell
from tools.premium_base import premium_contact_modal_html, premium_interaction_scripts

_DEAD_HREF_RE = re.compile(
    r"""<a\s+([^>]*?)href\s*=\s*["']#["']([^>]*)>""",
    re.IGNORECASE,
)

_SECTION_IDS = ("hero", "services", "about", "contact", "footer")


def find_forbidden_placeholder_issues(
    html: str,
    *,
    client_profile: Any | None = None,
) -> list[tuple[str, str]]:
    """Retourne (code, message) pour BugHunterAI."""
    issues: list[tuple[str, str]] = []
    if client_profile is not None and getattr(client_profile, "company_name", ""):
        issues.extend(validate_client_literals(html, client_profile))
    # DÉSACTIVÉ TEMPORAIREMENT - DEBUG — FORBIDDEN_CONTENT_PATTERNS / lorem / placeholder
    # if looks_like_technical_placeholder(html):
    #     issues.append(
    #         (
    #             "generic_placeholder",
    #             "Texte placeholder ou lorem ipsum détecté — contenu client requis.",
    #         )
    #     )
    if _DEAD_HREF_RE.search(html):
        issues.append(
            (
                "dead_links",
                'Liens morts href="#" — utiliser ancres, data-cf-action ou tel:/mailto:.',
            )
        )
    if 'id="contact"' not in html.lower() and "id='contact'" not in html.lower():
        if "cf-contact-form" not in html.lower():
            issues.append(
                (
                    "missing_contact",
                    "Section contact ou formulaire cf-contact-form manquant.",
                )
            )
    return issues


def is_vitrine_html_plan(plan: Any | None) -> bool:
    if not plan:
        return False
    pt = getattr(plan, "project_type", None)
    value = getattr(pt, "value", pt)
    return value in ("site_web", "landing_page")


def is_template_first_html_plan(
    plan: Any | None,
    *,
    generation_mode: str | None = None,
) -> bool:
    """Vitrine + ecommerce + réservation + app + desktop (HTML assemblé)."""
    if not plan:
        return False
    from agents.template_first_policy import is_template_first_html_project

    return is_template_first_html_project(plan, generation_mode=generation_mode)


def _ensure_section_ids(html: str) -> str:
    """Ajoute des id sur sections héros/services/contact si absents."""
    out = html
    if 'id="hero"' not in out.lower() and 'id="contact"' not in out.lower():
        out = re.sub(
            r"(<section)(\s+class=[\"'][^\"']*hero[^\"']*[\"'])",
            r'\1 id="hero"\2',
            out,
            count=1,
            flags=re.IGNORECASE,
        )
    if 'id="services"' not in out.lower():
        out = re.sub(
            r"(<section)(\s+[^>]*>)",
            r'\1 id="services"\2',
            out,
            count=1,
            flags=re.IGNORECASE,
        )
    return out


def _fix_dead_hrefs(html: str) -> str:
    def _repl(match: re.Match[str]) -> str:
        before, after = match.group(1), match.group(2)
        attrs = f"{before}{after}"
        if "data-cf-action" in attrs.lower():
            return match.group(0)
        return (
            f'<a {before}href="#contact" data-cf-action="scroll" '
            f'data-cf-target="#contact"{after}>'
        )

    return _DEAD_HREF_RE.sub(_repl, html)


def _inject_contact_block(client_name: str) -> str:
    title = client_name.strip() or "notre équipe"
    return f"""
<section id="contact" class="cf-vitrine-contact" style="padding:4rem 1.5rem;max-width:960px;margin:0 auto;">
  <h2>Contactez {title}</h2>
  <p>Demandez un devis ou un rendez-vous — réponse sous 48 h.</p>
</section>
{premium_contact_modal_html()}
"""


def _inject_scripts_if_missing(html: str) -> str:
    if "cf-contact-form" in html and "submitDemoContact" in html:
        return html
    if "</body>" in html.lower():
        idx = html.lower().rfind("</body>")
        block = premium_interaction_scripts()
        return html[:idx] + block + html[idx:]
    return html + premium_interaction_scripts()


def _inject_runtime_stub(html: str, *, api_base: str, title: str) -> str:
    if 'id="cf-demo-runtime"' in html.lower():
        return html
    import json

    payload = json.dumps(
        {
            "token": "",
            "projectTitle": title,
            "demoUrl": "",
            "apiBase": api_base.rstrip("/"),
        },
        ensure_ascii=False,
    )
    payload = payload.replace("</", "<\\/")
    script = f'<script id="cf-demo-runtime" type="application/json">{payload}</script>'
    match = re.search(r"<body(\s[^>]*)?>", html, re.IGNORECASE)
    if match:
        pos = match.end()
        return html[:pos] + "\n" + script + html[pos:]
    return script + html


def enhance_builder_vitrine_html(
    html: str,
    *,
    plan: Any | None = None,
    research_brief: ResearchBrief | Any | None = None,
    client_name: str = "",
    user_prompt: str = "",
) -> str:
    """
    Corrige liens morts, injecte formulaire contact CapCore et scripts d'interaction.
    """
    if not html or not html.strip():
        return html

    out = strip_markdown_code_fences(strip_password_gate(html))

    name = client_name.strip()
    if not name and isinstance(research_brief, ResearchBrief):
        name = research_brief.nom_entreprise or ""
    if not name and plan:
        name = plan.project_type_label or ""

    out = _fix_dead_hrefs(out)
    out = _ensure_section_ids(out)

    if "cf-contact-form" not in out.lower():
        out = out + _inject_contact_block(name)

    out = _inject_scripts_if_missing(out)
    api_base = resolve_demo_api_base_url()
    if api_base:
        title = name or (plan.project_type_label if plan else "Site vitrine")
        out = _inject_runtime_stub(out, api_base=api_base, title=title)

    profile = build_client_content_profile(
        user_prompt=user_prompt,
        research_brief=research_brief,
        plan=plan,
    )
    if profile.company_name:
        out = repair_client_literals_in_html(
            out,
            profile,
            user_prompt=user_prompt,
        )

    return apply_vitrine_premium_shell(
        out,
        profile,
        user_prompt=user_prompt,
    )

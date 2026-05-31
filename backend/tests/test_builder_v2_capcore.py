"""BuilderAI v2 — capcore-pro-site : template landing et contenu personnalisé."""

import asyncio

from agents.architect_agent import ArchitectAgent
from agents.coremind_agent import ProjectType
from agents.demo_quality import preview_html_from_generation
from tools.demo_pipeline import build_client_demo_document
from tools.demo_template_service import TEMPLATE_LANDING

CAPCORE_PROMPT = (
    "Site vitrine CapCore Pro — capcore-pro-site. "
    "Agence digitale premium : création de sites web, automatisation, IA. "
    "Thème noir #0D0D0D et or #C9A84C. "
    "Sections : hero CapCore Pro, services (sites web, automatisation, IA), contact."
)


def test_architect_capcore_selects_landing() -> None:
    agent = ArchitectAgent()
    plan, _ = asyncio.run(
        agent.plan_with_analysis(
            CAPCORE_PROMPT,
            project_type_hint=ProjectType.SITE_WEB,
        )
    )
    assert plan.template == TEMPLATE_LANDING
    assert plan.used_llm is False


def test_capcore_demo_pipeline_personalized_html() -> None:
    async def _run() -> str:
        doc = await build_client_demo_document(
            CAPCORE_PROMPT,
            project_type_label="Site vitrine",
        )
        html = preview_html_from_generation(
            doc.generation,
            title="Site vitrine",
            user_prompt=CAPCORE_PROMPT,
        )
        return html

    html = asyncio.run(_run())
    assert "cf-premium-landing" in html
    assert "CapCore" in html or "capcore" in html.lower()
    assert "Jean Dupont" not in html
    assert "Marie Martin" not in html


def test_preview_uses_generation_html_not_rerender() -> None:
    """Si le HTML livrable est valide, pas de re-rendu template."""
    custom_html = (
        "<!DOCTYPE html><html><head><title>CapCore Pro</title>"
        "<style>"
        + "body{margin:0;background:#0D0D0D;color:#F5F5F5;font-family:sans-serif;}"
        + "h1{color:#C9A84C;font-size:2.5rem;}.hero{padding:3rem;}"
        + ".nav{display:flex;gap:1rem;}.svc{margin:2rem;}.cta{background:#C9A84C;}"
        + ".feat{display:grid;}.card{padding:1rem;}.footer{margin-top:2rem;}"
        + "a{color:#C9A84C;}.btn{padding:0.5rem 1rem;}.wrap{max-width:960px;}"
        + ".logo{font-weight:bold;}.tagline{opacity:0.9;}.grid{display:flex;}"
        + ".contact{padding:2rem;}.form input{display:block;}"
        + "</style></head><body>"
        "<header class='nav'><span class='logo'>CapCore Pro</span></header>"
        "<section class='hero'><h1>CapCore Pro — agence digitale</h1>"
        "<p class='tagline'>Sites web, automatisation et IA sur mesure.</p></section>"
        "<section class='svc'><h2>Services</h2><p>Création de sites premium.</p></section>"
        "<footer class='footer'>Contact capcore.pro@gmail.com</footer>"
        "</body></html>"
    )
    from tools.codegen_service import CodeGenerateResult, GeneratedFile

    generation = CodeGenerateResult(
        summary="CapCore LLM",
        code=custom_html,
        files=[GeneratedFile(path="index.html", content=custom_html)],
        stack=["html"],
        model="test",
        provider="test",
        demo_seed={"template": "landing", "brand_name": "Autre Marque"},
    )
    preview = preview_html_from_generation(
        generation,
        title="Site vitrine",
        user_prompt=CAPCORE_PROMPT,
    )
    assert preview == custom_html
    assert "Autre Marque" not in preview or "CapCore Pro" in preview

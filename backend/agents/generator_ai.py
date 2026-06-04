"""
GeneratorAI — génère le HTML complet final en un seul appel Claude.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any

import anthropic
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

from config import get_settings
from security.llm_secrets import get_effective_llm_key

logger = logging.getLogger(__name__)

MODEL = os.getenv("COREMIND_SONNET_MODEL", "claude-sonnet-4-5")
MAX_TOKENS = 10000
MAX_HTML_CHARS = 15000

SYSTEM_PROMPT = """CRITIQUE : Tu DOIS inclure dans ta réponse :
- La balise <html> complète avec <head> et <body>
- Le nom exact du client dans <title> et dans <h1>
- Une balise <nav> ou <header>
- Au moins 3 balises <section>
- Un <footer>
- Au moins 3 balises <img class='pexels-inject'> (galerie / sections, PAS dans le hero)
- Zéro mot 'placeholder' dans le contenu visible

Le <footer> est OBLIGATOIRE. Place-le toujours en dernier élément
du <body>. Ne jamais terminer le HTML sans </footer></body></html>

VISUEL PREMIUM OBLIGATOIRE :
- Google Fonts : charger 2 fonts via <link> dans <head>
  (ex: Playfair Display pour titres + Inter pour corps de texte)
- Palette cohérente : utiliser les couleurs du brief partout
  (couleur_primaire pour CTAs, navbar, accents)
- Hero plein écran : PAS de <img> dans le hero — image en background-image CSS :
  .hero {
    background-image: url('...');
    background-size: cover;
    background-position: center;
    min-height: 100vh;
  }
  + overlay gradient semi-transparent, titre centré en blanc
- Animations reveal (progressive enhancement — visibles sans JS) :
  .reveal { opacity: 1; transform: none; transition: 0.6s; }
  Dans le JS au chargement : document.body.classList.add('js-loaded')
  .js-loaded .reveal { opacity: 0; transform: translateY(30px); }
  .js-loaded .reveal.visible { opacity: 1; transform: translateY(0); }
  + IntersectionObserver pour ajouter .visible au scroll si JS disponible
- Cards avec glassmorphism :
  background: rgba(255,255,255,0.1); backdrop-filter: blur(10px);
  border: 1px solid rgba(255,255,255,0.2); border-radius: 16px;
- Navbar fixe en haut avec blur :
  position: fixed; backdrop-filter: blur(20px);
  background: rgba(couleur_primaire, 0.9);
- Boutons premium : border-radius: 50px; padding: 14px 32px;
  transition: transform 0.2s; hover: transform: scale(1.05)
- Sections alternées : fond blanc puis fond couleur_primaire très clair
- Footer sombre avec couleur_primaire
- Responsive : media query max-width 768px obligatoire

Tu es un expert développeur web. Génère un site HTML complet,
visuellement premium, pour ce client.
RÈGLES STRICTES :
- HTML complet avec <head> et <body>
- CSS intégré dans <style> + variables --color-primary, --color-secondary
  depuis couleur_primaire et couleur_secondaire du brief
- Structure : navbar + hero plein écran + 3 sections contenu +
  galerie + contact + footer
- Tout le texte doit utiliser les vraies informations du brief
- Images contenu : <img class='pexels-inject'> (galerie, services — jamais le hero)
- Maximum 15000 caractères
- Zéro placeholder comme 'votre ville' ou 'à préciser'
- Zéro commentaire HTML

Réponds UNIQUEMENT avec le document HTML complet, sans texte avant ou après.

ABSOLUMENT OBLIGATOIRE : Termine TOUJOURS par ces balises dans cet ordre exact :
</section>
<footer>
<p>© {client_name}</p>
</footer>
</body>
</html>
Ne jamais arrêter la génération avant ces balises."""

_HTML_START_RE = re.compile(r"<!DOCTYPE\s+html|<html\b", re.I)


def _extract_html(raw: str) -> str:
    text = (raw or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if len(lines) > 2 else lines[1:])
        text = text.strip()
        if text.lower().startswith("html"):
            text = text[4:].strip()
    match = _HTML_START_RE.search(text)
    if match:
        text = text[match.start() :]
    close = text.lower().rfind("</html>")
    if close != -1:
        text = text[: close + len("</html>")]
    return text.strip()


def _build_user_message(
    brief: dict[str, Any],
    *,
    corrections: str | None = None,
) -> str:
    payload = {k: brief.get(k) for k in brief if not str(k).startswith("_")}
    extra = ""
    if brief.get("payment_config"):
        extra += "\n\n## payment_config\n" + json.dumps(
            brief["payment_config"], ensure_ascii=False, indent=2
        )[:4000]
    if brief.get("database_schema"):
        extra += "\n\n## database_schema\n" + json.dumps(
            brief["database_schema"], ensure_ascii=False, indent=2
        )[:4000]
    body = (
        "## Brief client (JSON)\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)[:12000]
        + extra
    )
    fix = (corrections or "").strip()
    if fix:
        return f"## CORRECTIONS\n{fix}\n\n{body}"
    return body


class GeneratorAI:
    async def run(
        self,
        brief: dict[str, Any],
        *,
        corrections: str | None = None,
    ) -> dict[str, Any]:
        api_key = get_effective_llm_key("ANTHROPIC_API_KEY", get_settings())
        if not api_key:
            logger.error("[GeneratorAI] ANTHROPIC_API_KEY absente")
            return {"html": "", "success": False}

        client = anthropic.Anthropic(api_key=api_key)
        user_message = _build_user_message(brief, corrections=corrections)

        def _call() -> str:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )
            parts: list[str] = []
            for block in response.content:
                text = getattr(block, "text", None)
                if text:
                    parts.append(text)
            return "".join(parts)

        try:
            raw = await asyncio.to_thread(_call)
            html = _extract_html(raw)
            if len(html) > MAX_HTML_CHARS:
                html = html[:MAX_HTML_CHARS]
                close = html.lower().rfind("</body>")
                if close != -1:
                    html = html[: close + len("</body>")] + "\n</html>"
                elif "</html>" not in html.lower():
                    html += "\n</html>"
            if not _HTML_START_RE.search(html):
                raise ValueError("HTML invalide")
            logger.info("[GeneratorAI] OK — %d caractères", len(html))
            return {"html": html, "success": True}
        except Exception as exc:
            logger.exception("[GeneratorAI] échec: %s", exc)
            return {"html": "", "success": False}

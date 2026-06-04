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

SITE_RESERVATION_APPENDIX = """
MODE SITE RÉSERVATION (project_type ou generation_mode == site_reservation) :
Page 100 % autonome — ZÉRO fetch, ZÉRO API externe. Tout en HTML + CSS + JavaScript inline.

Structure obligatoire (dans cet ordre) :
0) Hero slider plein écran (voir ci-dessous)
1) Section Bienvenue (#bienvenue) juste après le hero
2) Section hébergements (#hebergements) AVANT le calendrier
3) Section calendrier intégrée (#calendrier ou .calendar-wrap)
4) Section formulaire réservation (#reservation-form)

EXCEPTION MODE RÉSERVATION : le hero est un slider (pas le hero statique CSS du prompt
général). Les règles slider ci-dessous remplacent la consigne « une seule background-image ».

### Hero slider automatique (CSS + JS pur, min-height 100vh)
- 4 à 5 slides (.hero-slide) qui défilent automatiquement toutes les 4 secondes
- Chaque slide : fond visuel distinct via <img class="pexels-inject"> en position absolute
  couvrant le slide (object-fit: cover) OU background-image sur .hero-slide + img.pexels-inject
- Chaque slide a un sous-titre unique adapté au secteur du brief (camping ex. :
  « Séjour nature en famille », « Détente au bord de la piscine », « Aventure et découverte »,
  « Souvenirs inoubliables » — adapter pour hôtel, gîte, spa, etc.)
- Transition fondu entre slides (opacity 0 → 1, pas de slide brutal)
- Points de navigation (dots) en bas du hero, cliquables pour aller à une slide
- Le titre principal (nom_client du brief) reste visible en overlay sur TOUTES les slides
  (h1 fixe au-dessus du carrousel, z-index élevé)
- JS : setInterval 4000 ms pour passer à la slide suivante + gestion des dots + pause optionnelle
  au survol si souhaité

### Section « Bienvenue » (#bienvenue)
- Placée immédiatement après le hero slider
- Titre en Playfair Display : « Bienvenue au [nom_client] » (nom exact du brief)
- Texte chaleureux de 3 à 4 phrases généré à partir de la description du brief
  (ton accueillant, activités, cadre, promesse de séjour)
- Mise en page : texte à gauche, photo à droite (<img class="pexels-inject">)
- Fond blanc (#ffffff ou var blanc), typo titres Playfair Display, corps Inter
- Responsive : colonnes empilées sur mobile (photo sous le texte)

### Section hébergements (minimum 3 cards premium)
- Chaque card : <img class="pexels-inject">, nom, type (mobil-home / chalet / tente / caravane),
  capacité « X personnes », prix/nuit en € adapté au secteur du brief
- Attributs data sur chaque card : data-hebergement-id, data-hebergement-name,
  data-price-per-night (nombre entier euros)
- Bouton « Réserver » par card : au clic, remplit le champ hébergement du formulaire
  et scroll vers le formulaire

### Calendrier interactif (section « Disponibilités & Calendrier » — pas de popup)
- HTML : titre + boutons prev/next + légende (vert / gris / bleu) + DEUX conteneurs vides
  (ex. id="calendar-month-0" et id="calendar-month-1") que le JS remplit — ne pas laisser
  les grilles vides sans script d'initialisation
- Deux grilles côte à côte : mois courant + mois suivant (noms de mois affichés au-dessus)
- Clic 1 = date arrivée, clic 2 = date départ (si avant arrivée, réinitialiser)
- Synchroniser les champs date du formulaire (input type="date" ou texte readonly)

Le JavaScript du calendrier DOIT (obligatoire — grilles visibles dès l'ouverture) :
- Définir une fonction renderCalendars() qui construit les deux grilles en DOM
  (innerHTML ou createElement) à chaque rendu
- Appeler renderCalendars() immédiatement au chargement :
  document.addEventListener('DOMContentLoaded', renderCalendars) OU window.onload = renderCalendars
  (les deux grilles doivent être remplies sans clic utilisateur)
- Chaque grille affiche une ligne d'en-têtes : Lu Ma Me Je Ve Sa Di
- Remplir les cases avec les numéros de jours 1 … 28/29/30/31 (cases vides en début de mois
  si le 1er ne tombe pas un lundi)
- Colorier en #22c55e (vert) les jours disponibles (futurs, cliquables)
- Colorier en #9ca3af (gris) les jours passés (avant aujourd'hui) — non cliquables
- Colorier en #9ca3af les 8 premiers jours du mois suivant (simulation indisponible)
- Colorier en #3b82f6 (bleu) les jours sélectionnés (arrivée / départ)
- Les boutons prev/next rappellent renderCalendars() après changement de mois de référence

### Formulaire réservation
- Prénom, Nom, Email, Téléphone
- Hébergement sélectionné (select ou input readonly, id reservation-lodging)
- Date arrivée / Date départ (ids reservation-checkin, reservation-checkout)
- Nombre de nuits (readonly, calculé)
- Montant total (readonly, calculé)
- Ligne récap : « 3 nuits × 85€ = 255€ » (id price-breakdown)
- Bouton « Confirmer la réservation » : affiche un message succès stylé (#booking-success),
  pas d'envoi réseau

### JavaScript obligatoire (un seul <script> avant </body>)
- Hero slider : initialisation au chargement (slide active, autoplay 4 s, dots cliquables)
- renderCalendars() + DOMContentLoaded/window.onload comme ci-dessus (priorité absolue)
- État calendrier (mois affichés, sélection arrivée/départ) + recalcul après clic jour
- Recalcul automatique nuits et montant quand dates ou hébergement changent
- Formule affichée : « {n} nuits × {prix}€ = {total}€ »

### Design
- Google Fonts : Playfair Display + Inter (liens <link> dans <head>)
- couleur_primaire du brief pour navbar, boutons, accents calendrier
- Animations .reveal au scroll (IntersectionObserver)
- Responsive @media (max-width: 768px) : calendriers empilés verticalement
"""

_HTML_START_RE = re.compile(r"<!DOCTYPE\s+html|<html\b", re.I)


def _is_site_reservation_brief(brief: dict[str, Any]) -> bool:
    b = brief or {}
    for key in ("project_type", "generation_mode"):
        val = str(b.get(key) or "").strip().lower().replace("-", "_")
        if val == "site_reservation":
            return True
    return False


def _build_system_prompt(brief: dict[str, Any]) -> str:
    if _is_site_reservation_brief(brief):
        return SYSTEM_PROMPT + "\n" + SITE_RESERVATION_APPENDIX
    return SYSTEM_PROMPT


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
        system_prompt = _build_system_prompt(brief)

        def _call() -> str:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
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
            mode = "site_reservation" if _is_site_reservation_brief(brief) else "standard"
            logger.info("[GeneratorAI] OK (%s) — %d caractères", mode, len(html))
            return {"html": html, "success": True}
        except Exception as exc:
            logger.exception("[GeneratorAI] échec: %s", exc)
            return {"html": "", "success": False}

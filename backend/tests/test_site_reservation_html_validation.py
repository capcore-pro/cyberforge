"""Validation SupervisorAI — HTML démo site_reservation."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "supervisor_ai_test",
    _BACKEND / "agents" / "supervisor_ai.py",
)
assert _spec and _spec.loader
_supervisor_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_supervisor_mod)

SupervisorAI = _supervisor_mod.SupervisorAI
_is_site_reservation_brief = _supervisor_mod._is_site_reservation_brief
_site_reservation_html_errors = _supervisor_mod._site_reservation_html_errors


def _minimal_reservation_html() -> str:
    """HTML minimal valide pour les règles site_reservation (hors règles génériques)."""
    return """
    <html><head><title>Camping Test</title><style></style></head><body>
    <nav></nav>
    <section class="hero" style="min-height:100vh"></section>
    <section id="hebergements">
      <article class="hebergement-card" data-hebergement-id="1" data-price-per-night="80">
        <img class="pexels-inject"><button>Réserver</button>
      </article>
      <article class="hebergement-card" data-hebergement-id="2" data-price-per-night="95">
        <img class="pexels-inject"><button>Réserver</button>
      </article>
      <article class="hebergement-card" data-hebergement-id="3" data-price-per-night="70">
        <img class="pexels-inject">
      </article>
    </section>
    <section id="calendrier"><div id="booking-calendar" class="calendar-wrap"></div></section>
    <section>
      <form id="reservation-form">
        <input name="prenom"><input name="nom"><input name="email"><input name="telephone">
        <input id="reservation-checkin"><input id="reservation-checkout">
        <span id="price-breakdown"></span>
        <button>Confirmer la réservation</button>
      </form>
    </section>
    <footer></footer>
    <script>
      const calendar = { checkin: null, checkout: null };
      let nuits = 0;
      let montant = 0;
      let prix = 0;
      function updateTotal() {
        document.getElementById('price-breakdown').textContent =
          nuits + ' nuits × ' + prix + '€ = ' + montant + '€';
      }
    </script>
    </body></html>
    """


def test_is_site_reservation_brief() -> None:
    assert _is_site_reservation_brief({"project_type": "site_reservation"}) is True
    assert _is_site_reservation_brief({"generation_mode": "site_reservation"}) is True
    assert _is_site_reservation_brief({"project_type": "vitrine"}) is False


def test_site_reservation_errors_empty_calendar() -> None:
    html = "<div class='hebergement-card'></div><div class='hebergement-card'></div><form></form><script>nuit total prix calendrier arriv depart</script>"
    errs = _site_reservation_html_errors(html, html.lower())
    assert any("calendrier" in e for e in errs)


def test_site_reservation_errors_minimal_ok() -> None:
    html = _minimal_reservation_html()
    errs = _site_reservation_html_errors(html, html.lower())
    assert errs == []


def test_site_reservation_relaxed_form_and_js() -> None:
    """Un seul input + mot réservation + JS via onclick (pas de <script>)."""
    html = """
    <section id="calendrier"><div class="calendar"></div></section>
    <article class="hebergement-card" data-hebergement-id="1" data-price-per-night="80"></article>
    <article class="hebergement-card" data-hebergement-id="2" data-price-per-night="90"></article>
    <section id="formulaire-reservation">
      <input type="date" name="arriv">
      <button onclick="calcNuits(); updateTotal prix montant calendrier depart">Réserver</button>
    </section>
    """
    low = html.lower()
    errs = _site_reservation_html_errors(html, low)
    assert not any("incomplet" in e for e in errs)
    assert not any("balise <script>" in e for e in errs)
    assert errs == []


@pytest.mark.asyncio
async def test_validate_html_rejects_missing_closing_html() -> None:
    supervisor = SupervisorAI()
    brief = {"project_type": "vitrine", "client_name": "Test Client"}
    html = "<html><head><title>Test Client</title><style></style></head><body><nav></nav>"
    result = await supervisor.validate_html(html, brief)
    assert result.get("valid") is False
    assert any("document HTML incomplet" in e for e in (result.get("errors") or []))


@pytest.mark.asyncio
async def test_validate_html_adds_site_reservation_rules() -> None:
    """Sans calendrier, validate_html signale une erreur site_reservation."""
    supervisor = SupervisorAI()
    brief = {"project_type": "site_reservation", "client_name": "Camping Les Pins"}
    html = "<html><head><style></style></head><body><nav></body></html>"
    result = await supervisor.validate_html(html, brief)
    joined = " ".join(result.get("errors") or [])
    assert "site_reservation" in joined
    assert "calendrier" in joined

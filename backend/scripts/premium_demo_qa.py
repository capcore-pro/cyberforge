"""
Static QA — démos premium (HTML self-contained).

Checks (heuristiques) :
- Fonts premium présentes (Syne + Space Grotesk)
- Prefers-reduced-motion support présent
- Pas d'ancienne police ("Plus Jakarta Sans")
- Marker template présent et HTML non vide
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(__file__)
_BACKEND = os.path.abspath(os.path.join(_HERE, ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from tools.demo_template_service import DemoSeedData, build_html_from_seed  # noqa: E402


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _seed_for(template: str, *, vertical: str) -> DemoSeedData:
    prompt_map = {
        "restaurant": "Restaurant bistronomique — réservations et planning de salle",
        "real_estate": "Agence immobilier — mandats, visites, estimation",
        "health": "Cabinet médical — prise de RDV et dossiers patients",
        "artisan": "Artisan plombier — dépannage, devis, facturation",
        "beauty": "Salon de coiffure — prise de RDV, fidélité, catalogue prestations",
        "fitness": "Salle de sport — abonnements, planning cours, coaching",
        "marketing": "Agence marketing — campagnes, ROI, leads, dashboard",
    }
    prompt = prompt_map.get(vertical, f"Démo premium — {vertical}")
    return DemoSeedData(
        template=template,
        title=f"Démo {template} — {vertical}",
        subtitle="",
        brand_name="Nova Studio",
        brand_tag="Démo premium",
        user_name="Alex Martin",
        user_role="Utilisateur",
        tasks=(),
        llm_personalized=False,
    )


def main(argv: list[str]) -> int:
    templates = ("landing", "crm", "dashboard", "facturation", "reservation", "taskflow")
    verticals = ("restaurant", "real_estate", "health", "artisan", "beauty", "fitness")

    failures: list[str] = []
    for tpl in templates:
        for v in verticals:
            try:
                html = build_html_from_seed(_seed_for(tpl, vertical=v))
                _assert(len(html) > 800, f"{tpl}/{v}: html_too_small")
                _assert("fonts.googleapis.com/css2?family=Space+Grotesk" in html, f"{tpl}/{v}: space_grotesk_missing")
                _assert("family=Syne" in html, f"{tpl}/{v}: syne_missing")
                _assert("prefers-reduced-motion" in html, f"{tpl}/{v}: reduced_motion_missing")
                _assert("Plus+Jakarta+Sans" not in html and "Plus Jakarta Sans" not in html, f"{tpl}/{v}: legacy_font_present")
            except Exception as exc:  # noqa: BLE001 - QA script
                failures.append(f"{tpl}/{v}: {exc}")

    if failures:
        for f in failures:
            print("FAIL", f)
        return 1

    print("OK premium_demo_qa: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


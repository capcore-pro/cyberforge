"""
Validation Stripe sans compte réel — client test + pipeline e-commerce (sans Cloudflare).

Usage (depuis backend/) :
    python scripts/validate_stripe_e2e.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

_orphan_client_id: str | None = None

STRIPE_PK = "pk_test_CYBERFORGE_TEST_KEY"
CLIENT_NAME = "Client Test Stripe"
CLIENT_EMAIL = "test@cyberforge.dev"

MINIMAL_ECOM_HTML = """<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"><title>Boutique test CyberForge</title></head>
<body>
<main>
  <h1>Boutique fictive</h1>
  <button type="button" onclick="addToCart('Produit démo', 1, 24.99)">Ajouter au panier</button>
</body>
</html>
"""


async def _mock_brief_run(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    return {
        "client_name": CLIENT_NAME,
        "project_type": "ecommerce",
        "sector": "ecommerce_alimentaire",
        "description": "Boutique en ligne fictive pour test Stripe CyberForge.",
    }


async def _mock_generator_run(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    return {"success": True, "html": MINIMAL_ECOM_HTML}


async def _mock_payment_run(**_kwargs: Any) -> dict[str, Any]:
    return {"payment_type": "stripe", "provider": "stripe"}


async def _mock_supervisor_valid(**_kwargs: Any) -> dict[str, Any]:
    return {"valid": True, "errors": []}


async def _mock_deploy_html_demo(**kwargs: Any) -> tuple[str, str, str, str]:
    del kwargs
    return (
        "https://cyberforge.local/validation-stripe",
        "test-token",
        "test-pass",
        "https://cyberforge.local/unlock",
    )


async def _fake_run_supervised(
    _agent_name: str,
    run_once,
    _validate,
    *,
    initial_prompt: str = "",
    success_log=None,
):
    del success_log
    return await run_once(initial_prompt)


def main() -> int:
    global _orphan_client_id  # noqa: PLW0603
    from main import app

    client_id: str | None = None
    _orphan_client_id = None
    checks = {
        "js.stripe.com/v3": False,
        STRIPE_PK: False,
        "redirectToCheckout": False,
    }

    with (
        patch("pipeline._run_supervised", _fake_run_supervised),
        patch("agents.brief_ai.BriefAI.run", _mock_brief_run),
        patch("agents.generator_ai.GeneratorAI.run", _mock_generator_run),
        patch("agents.payment_ai.run", _mock_payment_run),
        patch("agents.supervisor_ai.SupervisorAI.validate_brief", _mock_supervisor_valid),
        patch("agents.supervisor_ai.SupervisorAI.validate_payment", _mock_supervisor_valid),
        patch("agents.supervisor_ai.SupervisorAI.validate_html", _mock_supervisor_valid),
        patch("agents.supervisor_ai.SupervisorAI.validate_deployment", _mock_supervisor_valid),
        patch("agents.deploy_ai.deploy_html_demo", _mock_deploy_html_demo),
        patch("agents.deploy_ai.inject_pexels_images", AsyncMock(side_effect=lambda html, **_: html)),
    ):
        tc = TestClient(app)

        create = tc.post(
            "/api/clients",
            json={
                "name": CLIENT_NAME,
                "email": CLIENT_EMAIL,
                "stripe_publishable_key": STRIPE_PK,
            },
        )
        if create.status_code not in (200, 201):
            print(f"FAIL create client HTTP {create.status_code}: {create.text[:300]}")
            return 1
        client_id = create.json().get("id")
        if not client_id:
            print("FAIL create client: id manquant")
            return 1
        _orphan_client_id = client_id
        print(f"OK client cree id={client_id}")

        gen = tc.post(
            "/api/generate/sync",
            json={
                "prompt": (
                    "TYPE: ecommerce\n"
                    f"Client : {CLIENT_NAME}\n"
                    "Boutique en ligne fictive — produits artisanaux, panier et paiement Stripe."
                ),
                "project_type": "ecommerce",
                "client_name": CLIENT_NAME,
                "stripe_publishable_key": STRIPE_PK,
            },
            timeout=120.0,
        )
        if gen.status_code != 200:
            print(f"FAIL generate HTTP {gen.status_code}: {gen.text[:500]}")
            return 1

        payload = gen.json()
        if not payload.get("success"):
            print(f"FAIL generate: {payload.get('error') or 'success=false'}")
            return 1

        html = str(payload.get("html") or "")
        if not html.strip():
            print("FAIL generate: HTML vide")
            return 1

        print(f"OK HTML reçu ({len(html)} caractères)")

        for needle in checks:
            checks[needle] = needle in html

        for label, ok in checks.items():
            print(f"{'OK' if ok else 'FAIL'} contient {label!r}")

        delete = tc.delete(f"/api/clients/{client_id}")
        client_id = None
        _orphan_client_id = None
        if delete.status_code != 200:
            print(f"WARN delete HTTP {delete.status_code}: {delete.text[:200]}")
        else:
            print("OK client test supprimé")

        if not all(checks.values()):
            return 1
        print("VALIDATION STRIPE E2E — tous les checks passent")
        return 0


if __name__ == "__main__":
    exit_code = 1
    try:
        exit_code = main()
    except Exception as exc:
        print(f"FAIL exception: {exc}")
        exit_code = 1
    finally:
        if _orphan_client_id:
            try:
                from main import app

                TestClient(app).delete(f"/api/clients/{_orphan_client_id}")
                print(f"OK client orphelin supprime id={_orphan_client_id}")
            except Exception:
                pass
    raise SystemExit(exit_code)

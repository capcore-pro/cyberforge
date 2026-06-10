"""Tests EmailAI — déploiement, commande, réservation (Brevo mocké)."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from agents.email_ai import (
    send_deployment_notification,
    send_order_confirmation,
    send_reservation_confirmation,
)


@pytest.fixture
def brief_boulangerie() -> dict[str, Any]:
    return {
        "client_name": "Aux Délices",
        "project_type": "vitrine_next",
        "sector": "boulangerie",
        "couleur_primaire": "#5C3A21",
        "design_system": {
            "style_family": "premium_light",
            "colors": {"primary": "#5C3A21"},
        },
    }


def test_deployment_notification_sends_html(brief_boulangerie: dict) -> None:
    asyncio.run(_test_deployment_notification_sends_html(brief_boulangerie))


async def _test_deployment_notification_sends_html(brief_boulangerie: dict) -> None:
    captured: dict[str, Any] = {}

    async def _capture(**kwargs: Any) -> str:
        captured.update(kwargs)
        return "msg-1"

    with (
        patch("agents.email_ai._brevo_configured", return_value=True),
        patch("agents.email_ai.send_html_email", side_effect=_capture),
    ):
        ok = await send_deployment_notification(
            brief=brief_boulangerie,
            demo_url="https://demo.test/aux-delices",
            duration_ms=125000,
        )

    assert ok is True
    assert "Aux Délices" in captured["subject"]
    assert "Vitrine" in captured["subject"]
    html = captured["html_content"]
    assert "Voir la démo" in html
    assert "premium_light" in html
    assert "#5C3A21" in html
    assert "02:05" in html
    assert "https://demo.test/aux-delices" in html


def test_deployment_notification_without_brevo(
    brief_boulangerie: dict, caplog: pytest.LogCaptureFixture
) -> None:
    asyncio.run(_test_deployment_notification_without_brevo(brief_boulangerie, caplog))


async def _test_deployment_notification_without_brevo(
    brief_boulangerie: dict, caplog: pytest.LogCaptureFixture
) -> None:
    with patch("agents.email_ai._brevo_configured", return_value=False):
        ok = await send_deployment_notification(
            brief=brief_boulangerie,
            demo_url="https://demo.test",
            duration_ms=1000,
        )
    assert ok is False
    assert any("Brevo non configuré" in r.message for r in caplog.records)


def test_order_confirmation_items_and_total() -> None:
    asyncio.run(_test_order_confirmation_items_and_total())


async def _test_order_confirmation_items_and_total() -> None:
    captured: dict[str, Any] = {}

    async def _capture(**kwargs: Any) -> str:
        captured.update(kwargs)
        return "msg-2"

    with (
        patch("agents.email_ai._brevo_configured", return_value=True),
        patch("agents.email_ai.send_html_email", side_effect=_capture),
    ):
        ok = await send_order_confirmation(
            order_data={
                "items": [
                    {"name": "Robe Éclat", "quantity": 2, "unit_amount": 4500},
                    {"name": "Livraison", "quantity": 1, "unit_amount": 500},
                ],
                "total": 95.0,
                "currency": "eur",
                "customer_email": "client@example.com",
            },
            shop_name="Maison Éclat",
            shop_url="https://shop.test",
            couleur_primaire="#d4a843",
        )

    assert ok is True
    assert "Maison Éclat" in captured["subject"]
    html = captured["html_content"]
    assert "Robe Éclat" in html
    assert "95€" in html
    assert "3-5 jours ouvrés" in html
    assert "Retourner à la boutique" in html


def test_reservation_confirmation_dates_and_price() -> None:
    asyncio.run(_test_reservation_confirmation_dates_and_price())


async def _test_reservation_confirmation_dates_and_price() -> None:
    captured: dict[str, Any] = {}

    async def _capture(**kwargs: Any) -> str:
        captured.update(kwargs)
        return "msg-3"

    with (
        patch("agents.email_ai._brevo_configured", return_value=True),
        patch("agents.email_ai.send_html_email", side_effect=_capture),
    ):
        ok = await send_reservation_confirmation(
            reservation_data={
                "guest_name": "Jean Dupont",
                "guest_email": "jean@example.com",
                "checkin": "12/06/2026 15:00",
                "checkout": "15/06/2026 11:00",
                "nights": 3,
                "total_price": 255.0,
                "property_contact": "contact@camping.test",
            },
            property_name="Camping Les Pins",
            property_url="https://camping.test",
            couleur_primaire="#1D9E75",
        )

    assert ok is True
    assert "Camping Les Pins" in captured["subject"]
    html = captured["html_content"]
    assert "12/06/2026" in html
    assert "255€" in html
    assert "Voir ma réservation" in html
    assert "contact@camping.test" in html


def test_all_functions_return_false_without_brevo(caplog: pytest.LogCaptureFixture) -> None:
    asyncio.run(_test_all_functions_return_false_without_brevo(caplog))


async def _test_all_functions_return_false_without_brevo(caplog: pytest.LogCaptureFixture) -> None:
    with patch("agents.email_ai._brevo_configured", return_value=False):
        r1 = await send_deployment_notification(
            brief={"client_name": "X"}, demo_url="https://x.test", duration_ms=1
        )
        r2 = await send_order_confirmation(
            order_data={"items": [], "total": 0, "customer_email": "a@b.c"},
            shop_name="Shop",
            shop_url="https://shop.test",
        )
        r3 = await send_reservation_confirmation(
            reservation_data={"guest_email": "a@b.c", "guest_name": "A"},
            property_name="P",
            property_url="https://p.test",
        )
    assert r1 is False and r2 is False and r3 is False
    assert sum(1 for r in caplog.records if "Brevo non configuré" in r.message) >= 3


def test_pipeline_triggers_deployment_email() -> None:
    asyncio.run(_test_pipeline_triggers_deployment_email())


async def _test_pipeline_triggers_deployment_email() -> None:
    from pipeline import PipelineRequest, run_pipeline

    minimal_html = "<!DOCTYPE html><html><body>" + ("x" * 3200) + "</body></html>"
    send_mock = AsyncMock(return_value=True)

    with (
        patch("pipeline.BriefAI") as brief_cls,
        patch("pipeline.GeneratorAI") as gen_cls,
        patch("pipeline.DeployAI") as dep_cls,
        patch("pipeline.SupervisorAI") as sup_cls,
        patch("agents.deploy_ai.deploy_html_demo", new_callable=AsyncMock) as mock_deploy,
        patch("agents.deploy_ai.inject_pexels_images", new_callable=AsyncMock) as mock_pexels,
        patch("agents.email_ai.send_deployment_notification", send_mock),
    ):
        brief_cls.return_value.run = AsyncMock(
            return_value={
                "client_name": "Aux Délices",
                "project_type": "vitrine_next",
                "sector": "boulangerie",
                "couleur_primaire": "#5C3A21",
                "description": "Boulangerie artisanale à Rouen avec pains et viennoiseries.",
                "services": ["Pain", "Viennoiseries", "Pâtisserie"],
                "ambiance": "chaleureux",
                "ville": "Rouen",
                "phone": "02 00 00 00 00",
                "email": "contact@test.fr",
            }
        )
        gen_cls.return_value.run = AsyncMock(
            return_value={"success": True, "html": minimal_html}
        )
        mock_pexels.side_effect = lambda html, **_: html
        mock_deploy.return_value = (
            "https://demo.test/site",
            "tok",
            "pass",
            "https://demo.test/unlock",
        )
        dep_cls.return_value.run = AsyncMock(
            return_value={
                "url": "https://demo.test/site",
                "success": True,
                "html": minimal_html,
            }
        )
        supervisor = sup_cls.return_value
        supervisor.validate_brief = AsyncMock(return_value={"valid": True, "errors": []})
        supervisor.validate_html = AsyncMock(return_value={"valid": True, "errors": []})
        supervisor.validate_deployment = AsyncMock(return_value={"valid": True, "errors": []})
        supervisor.validate_design_system = MagicMock(
            side_effect=lambda ds, _b: ds
        )

        await run_pipeline(
            PipelineRequest(prompt="Boulangerie Aux Délices", project_type="vitrine_next"),
            generation_id=None,
        )
        await asyncio.sleep(0.05)

    send_mock.assert_awaited_once()
    kwargs = send_mock.await_args.kwargs
    assert kwargs["demo_url"] == "https://demo.test/site"
    assert kwargs["brief"]["client_name"] == "Aux Délices"


def test_ecommerce_webhook_triggers_order_email() -> None:
    asyncio.run(_test_ecommerce_webhook_triggers_order_email())


async def _test_ecommerce_webhook_triggers_order_email() -> None:
    from api.routes.public_ecommerce import stripe_webhook

    send_mock = AsyncMock(return_value=True)
    project = {
        "id": "proj-1",
        "slug": "shop-test",
        "client_name": "Maison Éclat",
        "demo_url": "https://shop.test",
        "couleur_primaire": "#d4a843",
        "currency": "eur",
    }
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_123",
                "amount_total": 9500,
                "currency": "eur",
                "customer_details": {
                    "email": "buyer@example.com",
                    "name": "Buyer",
                },
                "metadata": {"order_id": "ord-1"},
                "line_items": {
                    "data": [
                        {
                            "quantity": 2,
                            "price": {
                                "unit_amount": 4500,
                                "product_data": {"name": "Robe Éclat"},
                            },
                        }
                    ]
                },
            }
        },
    }
    request = MagicMock()
    request.body = AsyncMock(return_value=json.dumps(event).encode())

    with (
        patch("api.routes.public_ecommerce._get_project", new_callable=AsyncMock, return_value=project),
        patch("api.routes.public_ecommerce.handle_webhook", return_value={"type": "checkout.session.completed"}),
        patch("api.routes.public_ecommerce.get_managed_projects_store") as store_cls,
        patch("agents.email_ai.send_order_confirmation", send_mock),
    ):
        store = store_cls.return_value
        store._rest_url = MagicMock(return_value="https://supabase.test/rest/v1")  # noqa: SLF001
        store._headers = MagicMock(return_value={})  # noqa: SLF001

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []
        with patch("api.routes.public_ecommerce.httpx.AsyncClient") as client_cls:
            client_cls.return_value.__aenter__.return_value.patch = AsyncMock(
                return_value=mock_resp
            )
            client_cls.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_resp
            )
            await stripe_webhook("shop-test", request, stripe_signature="sig")

        await asyncio.sleep(0.05)

    send_mock.assert_awaited_once()
    kwargs = send_mock.await_args.kwargs
    assert kwargs["customer_email"] == "buyer@example.com"
    assert kwargs["order_data"]["total"] == 95.0
    assert kwargs["shop_name"] == "Maison Éclat"


def test_reservation_reserve_triggers_email() -> None:
    asyncio.run(_test_reservation_reserve_triggers_email())


async def _test_reservation_reserve_triggers_email() -> None:
    from api.routes.public_reservation import ReserveRequest, reserve

    send_mock = AsyncMock(return_value=True)
    project = {
        "id": "proj-r",
        "slug": "camping-test",
        "client_name": "Camping Les Pins",
        "demo_url": "https://camping.test",
        "couleur_primaire": "#1D9E75",
    }
    body = ReserveRequest(
        service_id="svc-1",
        starts_at="2026-06-12T15:00:00Z",
        customer_name="Jean Dupont",
        customer_email="jean@example.com",
    )

    svc_resp = MagicMock(status_code=200)
    svc_resp.json.return_value = [{"id": "svc-1", "duration_min": 60, "price_cents": 8500, "active": True}]
    create_resp = MagicMock(status_code=200)
    create_resp.json.return_value = [{"id": "res-1", "status": "confirmed"}]

    with (
        patch("api.routes.public_reservation._get_project_by_slug", new_callable=AsyncMock, return_value=project),
        patch("api.routes.public_reservation.list_slots", new_callable=AsyncMock) as slots_mock,
        patch("api.routes.public_reservation.get_managed_projects_store") as store_cls,
        patch("agents.email_ai.send_reservation_confirmation", send_mock),
    ):
        slots_mock.return_value = MagicMock(
            slots=["2026-06-12T15:00:00Z"]
        )
        store = store_cls.return_value
        store._rest_url = MagicMock(return_value="https://supabase.test/rest/v1")  # noqa: SLF001
        store._headers = MagicMock(return_value={})  # noqa: SLF001
        store.get_project_auth = AsyncMock(
            return_value=MagicMock(client_email="contact@camping.test")
        )

        with patch("api.routes.public_reservation.httpx.AsyncClient") as client_cls:
            client = client_cls.return_value.__aenter__.return_value
            client.get = AsyncMock(return_value=svc_resp)
            client.post = AsyncMock(return_value=create_resp)
            result = await reserve("camping-test", body)

        await asyncio.sleep(0.05)

    assert result.reservation_id == "res-1"
    send_mock.assert_awaited_once()
    data = send_mock.await_args.kwargs["reservation_data"]
    assert data["guest_email"] == "jean@example.com"
    assert "12/06/2026" in data["checkin"]
    assert data["total_price"] == 85.0

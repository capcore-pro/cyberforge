"""Tests inject_stripe_checkout — panier local vs Stripe Checkout."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_deploy_ai_module():
    """Charge deploy_ai sans passer par agents/__init__.py (imports lourds)."""
    root = Path(__file__).resolve().parents[1]
    name = "deploy_ai_test_module"
    path = root / "agents" / "deploy_ai.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_deploy = _load_deploy_ai_module()
inject_cart_js = _deploy.inject_cart_js
inject_stripe_checkout = _deploy.inject_stripe_checkout

SAMPLE_HTML = """<!DOCTYPE html>
<html><head><title>Shop</title></head>
<body><button onclick="addToCart('x',1,9.99)">Buy</button></body></html>
"""

TEST_PK = "pk_test_51CyberForgeUnitTestKey"


def test_inject_stripe_with_publishable_key():
    html = inject_cart_js(SAMPLE_HTML)
    out = inject_stripe_checkout(
        html,
        project_type="ecommerce",
        payment_config={"publishable_key": TEST_PK},
    )
    assert "https://js.stripe.com/v3/" in out
    assert "redirectToCheckout" in out
    assert TEST_PK in out
    assert "submitOrder" in out
    assert "payment=success" in out
    assert "payment=cancelled" in out


def test_inject_stripe_without_key_unchanged_cart():
    html = inject_cart_js(SAMPLE_HTML)
    baseline = inject_stripe_checkout(
        html,
        project_type="ecommerce",
        payment_config=None,
    )
    assert "https://js.stripe.com/v3/" not in baseline
    assert "redirectToCheckout" not in baseline
    assert "window.cart" in baseline


def test_inject_stripe_skipped_for_vitrine():
    html = inject_cart_js(SAMPLE_HTML)
    out = inject_stripe_checkout(
        html,
        project_type="vitrine_next",
        payment_config={"publishable_key": TEST_PK},
    )
    assert "https://js.stripe.com/v3/" not in out


def test_stripe_key_not_logged(caplog):
    import logging

    html = inject_cart_js(SAMPLE_HTML)
    with caplog.at_level(logging.INFO):
        inject_stripe_checkout(
            html,
            project_type="ecommerce",
            payment_config={"publishable_key": TEST_PK},
        )
    combined = caplog.text
    assert TEST_PK not in combined

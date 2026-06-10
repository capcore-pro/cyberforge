"""Tests transmission clé Stripe dans le brief pipeline."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_apply_stripe_fn():
    from typing import Any

    root = Path(__file__).resolve().parents[1]
    lines = (root / "pipeline.py").read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("def _apply_stripe"))
    end = next(i for i, line in enumerate(lines) if line.startswith("class PipelineRequest"))
    namespace: dict[str, Any] = {"Any": Any}
    exec("\n".join(lines[start:end]), namespace)  # noqa: S102
    return namespace["_apply_stripe_publishable_key"]


_apply_stripe_publishable_key = _load_apply_stripe_fn()


def test_apply_stripe_sets_publishable_key():
    brief: dict = {"payment_config": {"payment_type": "stripe"}}
    _apply_stripe_publishable_key(brief, "pk_test_abc123")
    assert brief["payment_config"]["publishable_key"] == "pk_test_abc123"


def test_apply_stripe_clears_when_empty():
    brief: dict = {"payment_config": {"publishable_key": "pk_test_old"}}
    _apply_stripe_publishable_key(brief, None)
    assert brief["payment_config"]["publishable_key"] is None


def test_apply_stripe_creates_payment_config():
    brief: dict = {}
    _apply_stripe_publishable_key(brief, "pk_live_xyz")
    assert brief["payment_config"]["publishable_key"] == "pk_live_xyz"

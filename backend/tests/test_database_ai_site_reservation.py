"""Schéma par défaut DatabaseAI — site_reservation."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.modules.setdefault("anthropic", MagicMock())

_BACKEND = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "database_ai_test",
    _BACKEND / "agents" / "database_ai.py",
)
assert _spec and _spec.loader
_db_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_db_mod)
_default_schema = _db_mod._default_schema


def test_default_schema_site_reservation_tables() -> None:
    schema = _default_schema("site_reservation")
    names = {t["name"] for t in schema["tables"]}
    assert names == {"accommodations", "customers", "bookings", "blocked_dates"}
    sql = schema["sql"].lower()
    assert "accommodations" in sql
    assert "price_per_night_cents" in sql
    assert "check_in" in sql
    assert "blocked_dates" in sql

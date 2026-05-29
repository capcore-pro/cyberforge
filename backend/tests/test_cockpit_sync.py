"""Tests cockpit_sync — flush cost_tracker vers SQLite."""

from __future__ import annotations

import importlib
import tempfile
from pathlib import Path

import pytest

from cost_tracker import get_cost_summary, reset_cost, track_cost


@pytest.fixture()
def cockpit_db_isolated(monkeypatch: pytest.MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "cockpit_sync_test.db"
        monkeypatch.setattr("cockpit_db._DB_PATH", db_path)
        import cockpit_db
        import cockpit_sync

        importlib.reload(cockpit_db)
        importlib.reload(cockpit_sync)
        cockpit_db.init_db()
        yield cockpit_sync, cockpit_db


def test_flush_project_costs_persists_and_resets(
    cockpit_db_isolated: tuple[object, object],
) -> None:
    sync, db = cockpit_db_isolated
    pid = "proj-flush-1"
    reset_cost(pid)
    track_cost(pid, "replicate", {"images": 2})
    track_cost(pid, "claude_sonnet", {"input_tokens": 1000, "output_tokens": 500})

    db.set_balance("replicate", 10.0)
    db.set_balance("anthropic", 20.0)
    db.set_thresholds("replicate", warning_eur=100.0, critical_eur=50.0, urgent_eur=5.0)

    result = sync.flush_project_costs(pid)
    assert result["project_id"] == pid
    assert len(result["flushed"]) == 2
    assert get_cost_summary(pid)["total_eur"] == 0.0

    rep_balance = db.get_balance("replicate")
    assert rep_balance is not None
    assert float(rep_balance["balance_eur"]) == pytest.approx(10.0 - 0.004, rel=1e-6)

    txs = db.get_transactions("replicate", 10, tx_type="expense")
    assert any(t.get("project_id") == pid for t in txs)


def test_flush_skips_unknown_service(
    cockpit_db_isolated: tuple[object, object],
) -> None:
    sync, _db = cockpit_db_isolated
    pid = "proj-flush-unknown"
    reset_cost(pid)
    track_cost(pid, "unknown_vendor_xyz", {"requests": 1})

    # Force a positive cost by patching is hard — unknown maps to key with 0 cost from _compute_cost_eur
    # Use replicate key with manual inject
    from cost_tracker import costs_by_project, _lock

    reset_cost(pid)
    with _lock:
        costs_by_project[pid] = {
            "total_eur": 1.5,
            "by_service": {"unknown_vendor_xyz": {"cost_eur": 1.5, "calls": 1}},
            "updated_at": None,
            "architect_plan": None,
        }

    result = sync.flush_project_costs(pid)
    assert len(result["flushed"]) == 0
    assert len(result["skipped"]) == 1
    assert get_cost_summary(pid)["total_eur"] == 0.0

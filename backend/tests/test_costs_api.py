"""Tests cost_tracker — réponse API GET /projects/{id}/costs."""

from cost_tracker import (
    build_costs_api_response,
    reset_cost,
    set_architect_plan,
    track_cost,
)


def test_build_costs_api_response_margin() -> None:
    pid = "test-costs-margin"
    reset_cost(pid)
    track_cost(pid, "replicate", {"images": 1})
    set_architect_plan(
        pid,
        {
            "complexity_score": 7,
            "complexity_label": "Complexe",
            "market_price_min": 6000,
            "market_price_max": 15000,
            "suggested_price_min": 2400,
            "suggested_price_max": 6000,
        },
    )
    payload = build_costs_api_response(pid)
    assert payload["project_id"] == pid
    assert payload["total_eur"] == 0.002
    assert payload["by_service"]["replicate"] == 0.002
    assert payload["architect_plan"]["suggested_price_min"] == 2400
    assert payload["margin_multiplier"] == round(2400 / 0.002)
    reset_cost(pid)


def test_margin_null_when_no_cost() -> None:
    pid = "test-costs-empty"
    reset_cost(pid)
    set_architect_plan(
        pid,
        {
            "complexity_score": 3,
            "complexity_label": "Simple",
            "market_price_min": 300,
            "market_price_max": 600,
            "suggested_price_min": 120,
            "suggested_price_max": 240,
        },
    )
    payload = build_costs_api_response(pid)
    assert payload["total_eur"] == 0.0
    assert payload["margin_multiplier"] is None
    reset_cost(pid)

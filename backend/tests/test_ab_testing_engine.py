"""Tests ABTestingEngine — Volume 8 Module 5."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from agents.ab_testing_engine import ABTestingEngine
from api.main import create_app


def _benchmarks(scores: list[int]) -> list[dict]:
    return [{"quality_score": score} for score in scores]


def test_compare_returns_winner_with_benchmarks() -> None:
    store = MagicMock()
    store.get_by_slug = AsyncMock(
        side_effect=[
            {"id": "prompt-a-id", "slug": "prompt-a"},
            {"id": "prompt-b-id", "slug": "prompt-b"},
        ]
    )
    store.list_benchmarks = AsyncMock(
        side_effect=[
            _benchmarks([82, 80, 78]),
            _benchmarks([70, 68, 66]),
        ]
    )

    result = asyncio.run(
        ABTestingEngine(store=store).compare("prompt-a", "prompt-b", min_samples=3)
    )

    assert result["winner"] == "a"
    assert result["prompt_a"]["avg_score"] == pytest.approx(80.0)
    assert result["prompt_b"]["avg_score"] == pytest.approx(68.0)
    assert result["confidence"] == "high"
    assert "prompt-a" in result["recommendation"]


def test_compare_insufficient_data_without_benchmarks() -> None:
    store = MagicMock()
    store.get_by_slug = AsyncMock(
        side_effect=[
            {"id": "prompt-a-id", "slug": "prompt-a"},
            {"id": "prompt-b-id", "slug": "prompt-b"},
        ]
    )
    store.list_benchmarks = AsyncMock(return_value=[])

    result = asyncio.run(
        ABTestingEngine(store=store).compare("prompt-a", "prompt-b", min_samples=3)
    )

    assert result["winner"] == "insufficient_data"
    assert result["prompt_a"]["samples"] == 0
    assert result["prompt_b"]["samples"] == 0
    assert "Minimum 3 benchmarks" in result["recommendation"]


def test_compare_error_when_slug_missing() -> None:
    store = MagicMock()
    store.get_by_slug = AsyncMock(return_value=None)

    result = asyncio.run(
        ABTestingEngine(store=store).compare("missing-a", "missing-b")
    )

    assert result["winner"] == "error"
    assert "introuvables" in result["error"]


def test_ab_test_api_route() -> None:
    store = MagicMock()
    store.is_configured.return_value = True
    store.get_by_slug = AsyncMock(
        side_effect=[
            {"id": "a", "slug": "brief-v1"},
            {"id": "b", "slug": "brief-v2"},
        ]
    )
    store.list_benchmarks = AsyncMock(
        side_effect=[
            _benchmarks([90, 88, 86]),
            _benchmarks([75, 74, 73]),
        ]
    )

    engine = ABTestingEngine(store=store)

    with (
        patch("api.routes.prompts_library.get_prompt_store", return_value=store),
        patch("agents.ab_testing_engine.ab_testing_engine", engine),
    ):
        client = TestClient(create_app())
        res = client.post(
            "/api/prompts-library/ab-test",
            json={
                "prompt_slug_a": "brief-v1",
                "prompt_slug_b": "brief-v2",
                "min_samples": 3,
            },
        )

    assert res.status_code == 200, res.text
    data = res.json()
    assert data["winner"] == "a"
    assert data["prompt_a"]["avg_score"] == pytest.approx(88.0)

"""Tests media_db — table media_assets dans cockpit.db."""

from __future__ import annotations

import importlib
import tempfile
from pathlib import Path

import pytest


@pytest.fixture()
def media_db_module(monkeypatch: pytest.MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "media_test.db"
        monkeypatch.setattr("cockpit_db._DB_PATH", db_path)
        import cockpit_db
        import media_db

        importlib.reload(cockpit_db)
        importlib.reload(media_db)
        cockpit_db.init_db()
        yield media_db


def test_add_list_get_delete_asset(media_db_module) -> None:
    db = media_db_module
    asset = db.add_asset(
        filename="hero.jpg",
        type="image",
        mime_type="image/jpeg",
        size_bytes=1024,
        local_path="C:/cyberforge/media/hero.jpg",
        source="generated",
        tags=["boulangerie", "hero", "unsplash"],
        project_id="proj-1",
    )
    assert asset["id"]
    assert asset["tags"] == ["boulangerie", "hero", "unsplash"]

    listed = db.list_assets(type="image", project_id="proj-1", source="generated")
    assert len(listed) == 1
    assert listed[0]["filename"] == "hero.jpg"

    found = db.get_asset(asset["id"])
    assert found is not None
    assert found["mime_type"] == "image/jpeg"

    updated = db.update_asset_r2(
        asset["id"],
        "https://cdn.example/hero.jpg",
        "media/hero.jpg",
    )
    assert updated is not None
    assert updated["r2_url"] == "https://cdn.example/hero.jpg"

    assert db.delete_asset(asset["id"]) is True
    assert db.get_asset(asset["id"]) is None


def test_list_assets_search(media_db_module) -> None:
    db = media_db_module
    db.add_asset(
        filename="logo.png",
        type="image",
        mime_type="image/png",
        size_bytes=100,
        local_path="/tmp/logo.png",
        source="upload",
        tags=["branding"],
    )
    hits = db.list_assets(search="logo")
    assert len(hits) == 1
    assert db.list_assets(search="absent") == []

"""Tests media_storage — stockage local."""

from __future__ import annotations

import importlib
import tempfile
from pathlib import Path

import pytest


@pytest.fixture()
def storage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    media_dir = tmp_path / "media"
    monkeypatch.setenv("MEDIA_ROOT", str(media_dir))
    with tempfile.TemporaryDirectory() as db_tmp:
        db_path = Path(db_tmp) / "storage_test.db"
        monkeypatch.setattr("cockpit_db._DB_PATH", db_path)
        import cockpit_db
        import media_db
        import media_storage

        importlib.reload(cockpit_db)
        importlib.reload(media_db)
        importlib.reload(media_storage)
        cockpit_db.init_db()
        yield media_storage, media_db


def test_save_local_and_delete(storage) -> None:
    media_storage, _media_db = storage
    root = media_storage.media_root()
    assert root.exists()

    data = b"\xff\xd8\xff fake jpeg"
    path = media_storage.save_local(data, "photo.jpg", "image")
    assert Path(path).is_file()
    assert "images" in path.replace("\\", "/")

    asset = _media_db.add_asset(
        filename="photo.jpg",
        type="image",
        mime_type="image/jpeg",
        size_bytes=len(data),
        local_path=path,
        source="upload",
    )
    url = media_storage.get_local_url(path)
    assert url == f"/api/media/files/{asset['id']}"

    assert media_storage.delete_local(path) is True
    assert not Path(path).is_file()


def test_sync_to_r2_without_config_returns_none(storage) -> None:
    media_storage, _ = storage
    path = media_storage.save_local(b"zip", "a.zip", "zip")
    assert media_storage.sync_to_r2(path, "zips/test/a.zip") is None
    assert media_storage.sync_all_pending()["count"] == 0

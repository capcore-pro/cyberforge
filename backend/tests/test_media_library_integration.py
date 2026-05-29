"""Tests intégration médiathèque — try_save ne bloque pas."""

from __future__ import annotations

import importlib
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest


def test_try_save_generated_asset_swallows_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import asyncio

    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("MEDIA_ROOT", str(Path(tmp) / "media"))
        monkeypatch.setattr("cockpit_db._DB_PATH", Path(tmp) / "cockpit.db")
        import cockpit_db
        import tools.media_library as ml

        importlib.reload(cockpit_db)
        importlib.reload(ml)
        cockpit_db.init_db()

        with patch.object(
            ml,
            "save_generated_asset",
            new_callable=AsyncMock,
            side_effect=RuntimeError("db down"),
        ):
            result = asyncio.run(
                ml.try_save_generated_asset(
                    "https://example.com/x.png",
                    "x.png",
                    "p1",
                    "generated",
                )
            )
        assert result is None

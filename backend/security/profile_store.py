"""
Profil CapCore — persistance JSON locale (%LOCALAPPDATA%/CyberForge/profile.json).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_DEFAULT_PROFILE: dict[str, Any] = {
    "first_name": "Mat",
    "last_name": "",
    "title": "Fondateur CapCore",
    "email": "",
    "phone": "",
    "siret": "",
    "vat_number": "",
    "address_street": "",
    "address_postal_code": "",
    "address_city": "",
    "signature": "",
    "kbis_media_id": None,
}


def _profile_path() -> Path:
    base = (
        os.environ.get("LOCALAPPDATA")
        or os.environ.get("APPDATA")
        or str(Path.home())
    )
    root = Path(base) / "CyberForge"
    root.mkdir(parents=True, exist_ok=True)
    return root / "profile.json"


def load_profile() -> dict[str, Any]:
    path = _profile_path()
    if not path.is_file():
        return dict(_DEFAULT_PROFILE)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return dict(_DEFAULT_PROFILE)
        merged = dict(_DEFAULT_PROFILE)
        merged.update(raw)
        return merged
    except (OSError, json.JSONDecodeError):
        return dict(_DEFAULT_PROFILE)


def save_profile(data: dict[str, Any]) -> dict[str, Any]:
    current = load_profile()
    current.update(data)
    path = _profile_path()
    path.write_text(
        json.dumps(current, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return current

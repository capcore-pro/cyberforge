"""
Lecture / écriture sélective de backend/.env (clés profil CapCore).
"""

from __future__ import annotations

import re
from pathlib import Path

from config import _BACKEND, _ROOT

_ENV_PATHS = (_BACKEND / ".env", _ROOT / ".env")


def primary_env_path() -> Path:
    backend_env = _BACKEND / ".env"
    if backend_env.exists():
        return backend_env
    return _ROOT / ".env"


def read_env_value(key: str) -> str | None:
    key = key.strip()
    for path in _ENV_PATHS:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.strip().startswith("#") or "=" not in line:
                continue
            name, _, raw = line.partition("=")
            if name.strip() == key:
                value = raw.strip().strip('"').strip("'")
                return value if value else None
    return None


def upsert_env_vars(updates: dict[str, str | None]) -> Path:
    """
    Met à jour ou ajoute des variables dans backend/.env.
    Les valeurs ``None`` suppriment la clé.
    """
    path = primary_env_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    existing_lines: list[str] = []
    if path.exists():
        existing_lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()

    pending = {k.strip(): v for k, v in updates.items() if k.strip()}
    output: list[str] = []
    seen: set[str] = set()

    key_pattern = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=")

    for line in existing_lines:
        match = key_pattern.match(line.strip())
        if not match:
            output.append(line)
            continue
        name = match.group(1)
        if name not in pending:
            output.append(line)
            continue
        seen.add(name)
        value = pending.pop(name)
        if value is None:
            continue
        output.append(f"{name}={_quote_env_value(value)}")

    for name, value in pending.items():
        if name in seen or value is None:
            continue
        output.append(f"{name}={_quote_env_value(value)}")

    text = "\n".join(output).rstrip() + "\n"
    path.write_text(text, encoding="utf-8")
    return path


def _quote_env_value(value: str) -> str:
    clean = value.strip()
    if not clean:
        return '""'
    if re.search(r"[\s#\"'\\]", clean):
        escaped = clean.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return clean

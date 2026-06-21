"""Résolution des binaires FFmpeg / ffprobe (env → PATH)."""

from __future__ import annotations

import os
import shutil
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def _ensure_env_loaded() -> None:
    try:
        from config import load_env_files

        load_env_files()
    except ImportError:
        pass


def _normalize_executable(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = str(value).strip()
    if not trimmed:
        return None
    path = Path(trimmed)
    if path.is_file():
        return str(path.resolve())
    return None


def resolve_ffmpeg() -> str:
    _ensure_env_loaded()
    configured = _normalize_executable(os.environ.get("FFMPEG_PATH"))
    if configured:
        return configured

    found = shutil.which("ffmpeg")
    if found:
        return found

    raise RuntimeError(
        "FFmpeg introuvable. Définissez FFMPEG_PATH dans backend/.env "
        "ou ajoutez ffmpeg au PATH système."
    )


def resolve_ffprobe() -> str:
    _ensure_env_loaded()
    configured = _normalize_executable(os.environ.get("FFPROBE_PATH"))
    if configured:
        return configured

    found = shutil.which("ffprobe")
    if found:
        return found

    raise RuntimeError(
        "ffprobe introuvable. Définissez FFPROBE_PATH dans backend/.env "
        "ou ajoutez ffprobe au PATH système."
    )

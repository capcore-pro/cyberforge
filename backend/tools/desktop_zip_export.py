"""
Export ZIP package Electron — index.html + fichiers Electron pour build Windows.
"""

from __future__ import annotations

import io
import re
import unicodedata
import zipfile
from datetime import UTC, datetime

from tools.site_zip_export import slugify_project_title


def zip_filename_for_desktop(project_title: str, *, on_date: datetime | None = None) -> str:
    when = on_date or datetime.now(UTC)
    return f"{slugify_project_title(project_title)}-electron-{when.strftime('%Y-%m-%d')}.zip"


def build_desktop_package_zip(
    html: str,
    electron_files: dict[str, str],
    project_title: str,
    *,
    on_date: datetime | None = None,
) -> tuple[bytes, str]:
    """Construit l'archive ZIP Electron en mémoire."""
    index_html = (html or "").strip()
    if not index_html:
        raise ValueError("HTML vide")

    files: dict[str, str] = {"index.html": index_html}
    for name in ("main.js", "preload.js", "package.json", "instructions_build.md"):
        content = str(electron_files.get(name) or "").strip()
        if content:
            files[name] = content

    if "main.js" not in files or "package.json" not in files:
        raise ValueError("Fichiers Electron incomplets (main.js, package.json requis).")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.writestr(path, files[path].encode("utf-8"))

    filename = zip_filename_for_desktop(project_title, on_date=on_date)
    return buf.getvalue(), filename


def electron_files_from_generation_files(files: list[dict] | None) -> dict[str, str]:
    """Extrait les fichiers Electron depuis le tableau generations.files."""
    result: dict[str, str] = {}
    if not isinstance(files, list):
        return result
    for item in files:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "").strip().replace("\\", "/")
        base = path.split("/")[-1]
        if base in {"main.js", "preload.js", "package.json", "instructions_build.md"}:
            content = item.get("content")
            if isinstance(content, str) and content.strip():
                result[base] = content
    return result

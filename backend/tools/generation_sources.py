"""
Normalisation des sources de génération (TSX) — dé-enveloppe les réponses JSON LLM.
"""

from __future__ import annotations

import json
import re
from typing import Any


def _try_load_json_object(text: str) -> dict[str, Any] | None:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _extract_quoted_field(text: str, key: str) -> str | None:
    """Extrait une chaîne JSON (échappements gérés) même si l'objet global est tronqué."""
    marker = f'"{key}"'
    idx = text.find(marker)
    if idx < 0:
        return None
    rest = text[idx + len(marker) :]
    colon = rest.find(":")
    if colon < 0:
        return None
    rest = rest[colon + 1 :].lstrip()
    if not rest.startswith('"'):
        return None
    i = 1
    out: list[str] = []
    while i < len(rest):
        ch = rest[i]
        if ch == "\\" and i + 1 < len(rest):
            nxt = rest[i + 1]
            if nxt == "n":
                out.append("\n")
            elif nxt == "t":
                out.append("\t")
            elif nxt == "r":
                out.append("\r")
            elif nxt == '"':
                out.append('"')
            elif nxt == "\\":
                out.append("\\")
            else:
                out.append(nxt)
            i += 2
            continue
        if ch == '"':
            break
        out.append(ch)
        i += 1
    return "".join(out)


def _unwrap_payload_dict(data: dict[str, Any]) -> tuple[list[dict[str, str]], str]:
    files_raw = data.get("files") or []
    files: list[dict[str, str]] = []
    for item in files_raw:
        if isinstance(item, dict) and item.get("path") is not None:
            files.append(
                {
                    "path": str(item["path"]).strip(),
                    "content": str(item.get("content") or ""),
                }
            )

    code = str(data.get("code") or "").strip()
    if not code and files:
        code = files[0]["content"].strip()
    if not files and code:
        path = "src/App.tsx"
        if code.lstrip().startswith("<!") or "<html" in code.lower()[:500]:
            path = "index.html"
        files = [{"path": path, "content": code}]
    return files, code


def _unwrap_text_blob(text: str) -> tuple[list[dict[str, str]], str] | None:
    stripped = text.strip()
    if not stripped.startswith("{"):
        return None
    if '"code"' not in stripped and '"files"' not in stripped:
        return None

    parsed = _try_load_json_object(stripped)
    if parsed is not None:
        return _unwrap_payload_dict(parsed)

    code = _extract_quoted_field(stripped, "code")
    if code and len(code) > 20:
        return _unwrap_payload_dict({"code": code, "files": []})

    return None


def normalize_generation_sources(
    files: list[dict[str, str]],
    code: str | None = None,
) -> tuple[list[dict[str, str]], str | None]:
    """
    Retourne des fichiers TSX/HTML exploitables.
    Corrige le cas où le LLM a stocké l'enveloppe JSON entière dans code ou files[0].content.
    """
    normalized_files = [
        {"path": f["path"].strip(), "content": f["content"]}
        for f in files
        if f.get("path")
    ]
    normalized_code = (code or "").strip() or None

    if normalized_code:
        unwrapped = _unwrap_text_blob(normalized_code)
        if unwrapped is not None:
            return unwrapped

    if len(normalized_files) == 1:
        unwrapped = _unwrap_text_blob(normalized_files[0]["content"])
        if unwrapped is not None:
            return unwrapped

    if len(normalized_files) > 1:
        for entry in normalized_files:
            unwrapped = _unwrap_text_blob(entry["content"])
            if unwrapped is not None:
                return unwrapped

    return normalized_files, normalized_code


def is_usable_preview_html(html: str | None) -> bool:
    """Détecte un aperçu HTML cassé (JSON échappé, corps vide)."""
    if not html or not html.strip():
        return False
    s = html.strip()
    if len(s) < 400:
        return False
    lower = s.lower()
    if "<!doctype" not in lower and "<html" not in lower:
        return False
    if re.search(r'id=["\']cf-demo-root["\']>\s*\\n', s):
        return False
    if re.search(r'class=\\"', s):
        return False
    root_match = re.search(
        r'id=["\']cf-demo-root["\']>([\s\S]*?)</div>\s*<script>',
        s,
        re.I,
    )
    if root_match:
        inner = root_match.group(1).strip()
        if len(inner) < 80 or inner in (r"\n", "\\n"):
            return False
        if "<" not in inner and ">" not in inner:
            return False
    return True

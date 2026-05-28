"""Copie le template Next.js et injecte content/site.json."""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

import httpx

from config import get_settings, plain_secret_str
from tools.vitrine.content_schema import VitrineSiteContent

logger = logging.getLogger(__name__)

_TEMPLATE_DIR_CACHE: Path | None = None


def _find_template_dir() -> Path:
    """
    Résout le chemin du template de manière robuste, même si le backend est
    déployé depuis un sous-dossier (ex: working dir = backend/ sur Railway).
    """
    candidates: list[Path] = []
    bases = [Path(__file__).resolve(), Path.cwd().resolve()]
    for base in bases:
        for parent in [base, *base.parents[:10]]:
            candidates.append(parent / "templates" / "vitrine-next")
    for path in candidates:
        if path.is_dir():
            return path

    # Fallback: download template from GitHub (useful when backend is deployed from a subdir)
    try:
        downloaded = _ensure_downloaded_template()
        if downloaded.is_dir():
            return downloaded
    except Exception as exc:
        logger.warning("Template download fallback failed: %s", exc)

    raise ScaffoldRenderError(
        "Template introuvable : templates/vitrine-next (candidates tried: "
        + ", ".join(str(p) for p in candidates[:6])
        + ("…" if len(candidates) > 6 else "")
        + ")"
    )

SITE_JSON_REL = Path("content") / "site.json"

_COPY_IGNORE_NAMES = {
    "node_modules",
    ".next",
    "out",
    ".git",
    "__pycache__",
}


class ScaffoldRenderError(Exception):
    """Échec copie ou écriture du scaffold vitrine."""


@dataclass(frozen=True)
class ScaffoldResult:
    output_dir: Path
    site_json_path: Path
    files: list[str]


def vitrine_template_dir() -> Path:
    global _TEMPLATE_DIR_CACHE
    if _TEMPLATE_DIR_CACHE is None:
        _TEMPLATE_DIR_CACHE = _find_template_dir()
    return _TEMPLATE_DIR_CACHE


def _ensure_downloaded_template() -> Path:
    """
    Télécharge `templates/vitrine-next` depuis le repo CyberForge si absent localement.
    Cache disque: /tmp/cyberforge-templates/vitrine-next (ou équivalent Windows).
    """
    settings = get_settings()
    repo = (settings.github_repo or "capcore-pro/cyberforge").strip() or "capcore-pro/cyberforge"
    token = plain_secret_str(settings.github_token)

    cache_root = Path.cwd() / ".template-cache"
    cache_root.mkdir(parents=True, exist_ok=True)
    dest = cache_root / "vitrine-next"
    marker = dest / ".cyberforge_template_downloaded"
    if marker.is_file() and dest.is_dir():
        return dest

    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)

    owner, name = repo.split("/", 1) if "/" in repo else ("capcore-pro", repo)
    api = f"https://api.github.com/repos/{owner}/{name}/contents/templates/vitrine-next"

    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    def _download_dir(url: str, out_dir: Path) -> None:
        with httpx.Client(timeout=60.0) as client:
            r = client.get(url, headers=headers, params={"ref": "main"})
            r.raise_for_status()
            items = r.json()
            if not isinstance(items, list):
                raise RuntimeError("GitHub contents API unexpected response.")
            for item in items:
                if not isinstance(item, dict):
                    continue
                t = item.get("type")
                path = str(item.get("path") or "")
                # ignore build artifacts if present
                if "/.next" in path or "/node_modules" in path:
                    continue
                if t == "dir":
                    sub = out_dir / Path(path).name
                    sub.mkdir(parents=True, exist_ok=True)
                    _download_dir(str(item.get("url")), sub)
                elif t == "file":
                    download_url = item.get("download_url")
                    if not download_url:
                        continue
                    fr = client.get(str(download_url), headers=headers)
                    fr.raise_for_status()
                    (out_dir / Path(path).name).write_bytes(fr.content)

    _download_dir(api, dest)
    marker.write_text("ok\n", encoding="utf-8")
    return dest


def _ignore_copy(_dir: str, names: list[str]) -> set[str]:
    return {name for name in names if name in _COPY_IGNORE_NAMES}


def _collect_relative_files(root: Path) -> list[str]:
    paths: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            paths.append(path.relative_to(root).as_posix())
    return paths


def render_vitrine_scaffold(
    content: VitrineSiteContent,
    *,
    output_dir: Path | None = None,
) -> ScaffoldResult:
    """
    Duplique templates/vitrine-next vers output_dir et écrit le JSON de contenu.
    """
    template = vitrine_template_dir()
    # default output under backend/.vitrine-builds
    backend_root = Path(__file__).resolve().parents[2]
    target = output_dir or (backend_root / ".vitrine-builds" / _slug_dir(content))
    target = target.resolve()

    if target.exists():
        shutil.rmtree(target)

    shutil.copytree(template, target, ignore=_ignore_copy)

    site_path = target / SITE_JSON_REL
    site_path.parent.mkdir(parents=True, exist_ok=True)
    payload = content.model_dump(mode="json", by_alias=True)
    site_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    files = _collect_relative_files(target)
    logger.info(
        "Scaffold vitrine | dir=%s | files=%s | business=%s",
        target,
        len(files),
        content.meta.businessName,
    )
    return ScaffoldResult(
        output_dir=target,
        site_json_path=site_path,
        files=files,
    )


def read_site_json_from_dir(project_dir: Path) -> VitrineSiteContent:
    path = project_dir / SITE_JSON_REL
    if not path.is_file():
        raise ScaffoldRenderError(f"site.json absent : {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return VitrineSiteContent.model_validate(raw)


def load_example_content() -> VitrineSiteContent:
    example_path = vitrine_template_dir() / SITE_JSON_REL
    raw = json.loads(example_path.read_text(encoding="utf-8"))
    return VitrineSiteContent.model_validate(raw)


def _slug_dir(content: VitrineSiteContent) -> str:
    slug = "".join(
        ch if ch.isalnum() else "-"
        for ch in content.meta.businessName.lower()
    ).strip("-")
    return slug[:40] or "vitrine-site"

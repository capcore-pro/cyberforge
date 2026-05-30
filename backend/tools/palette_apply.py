"""Application d'une palette toolbox à un projet managé (GitHub + redéploiement)."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from agents.architect_agent import ArchitectPlan, ToolboxPalette, ToolboxTypo
from agents.coremind_agent import ProjectType
from config import get_settings
from db.managed_projects_store import get_managed_projects_store
from tools.export_github import get_github_file, put_github_file
from tools.toolbox_branding import (
    _css_variables_block,
    _patch_file_content,
    google_fonts_stylesheet_url,
    hex_to_hsl_channels,
)
from tools.vercel_api import trigger_git_deploy, wait_for_deployment_ready

logger = logging.getLogger(__name__)

_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

_GITHUB_CSS_PATHS = (
    "app/globals.css",
    "src/index.css",
    "src/styles/globals.css",
    "styles/globals.css",
)


def _sanitize_hex(value: str, fallback: str = "#0284c7") -> str:
    cleaned = value.strip()
    if _HEX_RE.match(cleaned):
        return cleaned
    return fallback


def build_palette_plan(
    *,
    primary: str,
    secondary: str,
    accent: str,
    heading: str = "Inter",
    body: str = "Inter",
    secteur: str | None = None,
) -> ArchitectPlan:
    return ArchitectPlan(
        project_type=ProjectType.SITE_WEB,
        project_type_label="Site web",
        template="default",
        template_label="Default",
        rationale="Application palette toolbox",
        secteur=secteur,
        palette=ToolboxPalette(
            primary=_sanitize_hex(primary),
            secondary=_sanitize_hex(secondary),
            accent=_sanitize_hex(accent),
        ),
        typo=ToolboxTypo(heading=heading.strip() or "Inter", body=body.strip() or "Inter"),
        complexity_score=1,
        complexity_label="Simple",
        market_price_min=0,
        market_price_max=0,
        suggested_price_min=0,
        suggested_price_max=0,
    )


def patch_globals_css_content(css: str, plan: ArchitectPlan) -> str:
    if not plan.palette:
        return css
    p = plan.palette
    primary_hsl = hex_to_hsl_channels(p.primary)
    secondary_hsl = hex_to_hsl_channels(p.secondary)
    accent_hsl = hex_to_hsl_channels(p.accent)
    replacements = {
        r"--primary:\s*[^;]+;": f"--primary: {primary_hsl};",
        r"--secondary:\s*[^;]+;": f"--secondary: {secondary_hsl};",
        r"--accent:\s*[^;]+;": f"--accent: {accent_hsl};",
        r"--ring:\s*[^;]+;": f"--ring: {primary_hsl};",
        r"--cf-primary:\s*[^;]+;": f"--cf-primary: {p.primary};",
        r"--cf-secondary:\s*[^;]+;": f"--cf-secondary: {p.secondary};",
        r"--cf-accent:\s*[^;]+;": f"--cf-accent: {p.accent};",
    }
    for pattern, repl in replacements.items():
        css, _ = re.subn(pattern, repl, css, count=1)
    if "--cf-primary" not in css:
        css = _css_variables_block(plan) + "\n" + css
    return css


def patch_layout_tsx_content(layout: str, plan: ArchitectPlan) -> str:
    if not plan.palette:
        return layout
    p = plan.palette
    primary_hsl = hex_to_hsl_channels(p.primary)
    secondary_hsl = hex_to_hsl_channels(p.secondary)
    accent_hsl = hex_to_hsl_channels(p.accent)
    if plan.typo:
        url = google_fonts_stylesheet_url(plan.typo.heading, plan.typo.body)
        if url and url not in layout:
            layout = layout.replace(
                'import "./globals.css";',
                f'import "./globals.css";\n\nexport const toolboxFontsUrl = "{url}";',
                1,
            )
    if '"--primary"' in layout:
        layout = re.sub(
            r'("--primary":\s*)"[^"]*"',
            rf'\1"{primary_hsl}"',
            layout,
            count=1,
        )
        layout = re.sub(
            r'("--ring":\s*)"[^"]*"',
            rf'\1"{primary_hsl}"',
            layout,
            count=1,
        )
        layout = re.sub(
            r'("--secondary":\s*)"[^"]*"',
            rf'\1"{secondary_hsl}"',
            layout,
            count=1,
        )
        layout = re.sub(
            r'("--accent":\s*)"[^"]*"',
            rf'\1"{accent_hsl}"',
            layout,
            count=1,
        )
    return layout


def patch_site_json_content(raw: str, plan: ArchitectPlan) -> str:
    if not plan.palette:
        return raw
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    if isinstance(data, dict) and isinstance(data.get("meta"), dict):
        data["meta"]["primaryColor"] = plan.palette.primary
        return json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    return raw


async def _patch_github_path(
    *,
    repo: str,
    branch: str,
    path: str,
    new_content: str,
    message: str,
    settings: Any,
) -> bool:
    try:
        sha, raw = await get_github_file(
            repo=repo,
            branch=branch,
            path=path,
            settings=settings,
        )
    except Exception:
        return False
    if raw == new_content:
        return False
    await put_github_file(
        repo=repo,
        branch=branch,
        path=path,
        content_utf8=new_content,
        sha=sha,
        message=message,
        settings=settings,
    )
    return True


async def apply_palette_to_managed_project(
    project_id: str,
    *,
    primary: str,
    secondary: str,
    accent: str,
    heading: str = "Inter",
    body: str = "Inter",
    secteur: str | None = None,
) -> dict[str, Any]:
    """Applique la palette sur GitHub et déclenche un redéploiement Vercel si possible."""
    store = get_managed_projects_store()
    if not store.is_configured():
        raise ValueError("Store projets managés non configuré.")

    project = await store.get_project(project_id)
    if not project or project.deleted_at:
        raise ValueError("Projet introuvable.")
    if not project.github_repo or not project.github_branch:
        raise ValueError("Ce projet n'a pas de dépôt GitHub associé.")

    plan = build_palette_plan(
        primary=primary,
        secondary=secondary,
        accent=accent,
        heading=heading,
        body=body,
        secteur=secteur,
    )
    settings = get_settings()
    run = await store.create_run(project_id, action="apply_palette")
    await store.update_project(project_id, patch={"status": "building", "error_last": None})

    async def _run() -> None:
        patched_files: list[str] = []
        try:
            # site.json (vitrine)
            try:
                sha, raw = await get_github_file(
                    repo=project.github_repo,
                    branch=project.github_branch,
                    path="content/site.json",
                    settings=settings,
                )
                new_json = patch_site_json_content(raw, plan)
                if new_json != raw:
                    await put_github_file(
                        repo=project.github_repo,
                        branch=project.github_branch,
                        path="content/site.json",
                        content_utf8=new_json,
                        sha=sha,
                        message="CyberForge: apply toolbox palette (site.json)",
                        settings=settings,
                    )
                    patched_files.append("content/site.json")
            except Exception:
                pass

            for css_path in _GITHUB_CSS_PATHS:
                try:
                    sha, raw = await get_github_file(
                        repo=project.github_repo,
                        branch=project.github_branch,
                        path=css_path,
                        settings=settings,
                    )
                except Exception:
                    continue
                new_css = patch_globals_css_content(raw, plan)
                if new_css != raw:
                    await put_github_file(
                        repo=project.github_repo,
                        branch=project.github_branch,
                        path=css_path,
                        content_utf8=new_css,
                        sha=sha,
                        message=f"CyberForge: apply toolbox palette ({css_path})",
                        settings=settings,
                    )
                    patched_files.append(css_path)

            try:
                sha, raw = await get_github_file(
                    repo=project.github_repo,
                    branch=project.github_branch,
                    path="app/layout.tsx",
                    settings=settings,
                )
                new_layout = patch_layout_tsx_content(raw, plan)
                if new_layout != raw:
                    await put_github_file(
                        repo=project.github_repo,
                        branch=project.github_branch,
                        path="app/layout.tsx",
                        content_utf8=new_layout,
                        sha=sha,
                        message="CyberForge: apply toolbox palette (layout.tsx)",
                        settings=settings,
                    )
                    patched_files.append("app/layout.tsx")
            except Exception:
                pass

            # HTML / CSS générés (apps web)
            for extra_path in ("index.html", "src/App.css", "src/toolbox-theme.css"):
                try:
                    sha, raw = await get_github_file(
                        repo=project.github_repo,
                        branch=project.github_branch,
                        path=extra_path,
                        settings=settings,
                    )
                except Exception:
                    continue
                new_content = _patch_file_content(extra_path, raw, plan)
                if new_content != raw:
                    await put_github_file(
                        repo=project.github_repo,
                        branch=project.github_branch,
                        path=extra_path,
                        content_utf8=new_content,
                        sha=sha,
                        message=f"CyberForge: apply toolbox palette ({extra_path})",
                        settings=settings,
                    )
                    patched_files.append(extra_path)

            if not patched_files:
                raise ValueError("Aucun fichier CSS trouvé sur le dépôt du projet.")

            org, repo_name = project.github_repo.split("/", 1)
            triggered = None
            last_exc: Exception | None = None
            for attempt in range(3):
                try:
                    triggered = await trigger_git_deploy(
                        project_name=project.github_branch,
                        github_org=org,
                        github_repo=repo_name,
                        git_ref=project.github_branch,
                        settings=settings,
                    )
                    break
                except Exception as exc:
                    last_exc = exc
                    await asyncio.sleep(2.0 + attempt * 2.0)
            if triggered is None:
                raise last_exc or RuntimeError("Déclenchement Vercel impossible.")

            dep = await wait_for_deployment_ready(
                triggered.id, settings=settings, timeout_seconds=300.0
            )
            url_preview = f"https://{dep.url}" if dep.url else None
            url_production = f"https://{project.github_branch}.vercel.app"
            status = "deployed" if dep.ready_state == "READY" else "failed"
            await store.update_project(
                project_id,
                patch={
                    "status": status,
                    "vercel_deployment_id_last": dep.id,
                    "url_preview": url_preview,
                    "url_production": url_production if status == "deployed" else url_preview,
                    "error_last": None if status == "deployed" else "Échec déploiement Vercel",
                },
            )
            await store.finish_run(
                run.id,
                status="succeeded" if status == "deployed" else "failed",
                error=None if status == "deployed" else "Échec déploiement Vercel",
                artifacts={"patched_files": patched_files, "vercel_deployment_id": dep.id},
            )
        except Exception as exc:
            logger.exception("apply_palette_to_managed_project failed")
            await store.update_project(
                project_id, patch={"status": "failed", "error_last": str(exc)}
            )
            await store.finish_run(run.id, status="failed", error=str(exc))

    asyncio.create_task(_run())
    return {"scheduled": True, "run_id": run.id, "message": "Palette appliquée — redéploiement en cours"}

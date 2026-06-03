"""
ExportAI — déploiement automatique (Cloudflare, Railway, GitHub) + manifeste universel.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from agents.architect_agent import ArchitectPlan
from agents.base_agent import BaseAgent
from agents.coremind_agent import CoreMindAnalysis, ProjectType
from config import Settings, plain_secret_str
from tools.codegen_service import CodeGenerateResult
from tools.cloudflare_pages import pages_token_slug
from tools.deploy_manifest import (
    build_deploy_manifest,
    select_export_provider,
    slugify_project_name,
    unique_deploy_slug,
)
from tools.export_cloudflare import (
    CloudflareExportError,
    deploy_dedicated_pages,
    deploy_html_demo,
)
from tools.export_github import (
    DEFAULT_VITRINES_REPO,
    push_source_to_github,
    push_vitrine_site_to_github,
    vitrine_branch_name,
)
from tools.export_railway import RailwayExportError, deploy_to_railway
from cost_tracker import maybe_track_cost
from tools.export_html_resolve import (
    log_export_upload_source,
    resolve_export_html_for_upload,
)
from tools.generation_sources import is_usable_preview_html

logger = logging.getLogger(__name__)


class ExportResult(BaseModel):
    """Résultat ExportAI pour le pipeline et le Générateur."""

    agent_id: str = "export"
    agent_name: str = "ExportAI"
    success: bool = False
    provider: str = "cloudflare"
    production_url: str | None = None
    artifact_download_url: str | None = None
    github_url: str | None = None
    demo_token: str | None = None
    demo_password: str | None = None
    unlock_url: str | None = None
    manifest: dict[str, Any] = Field(default_factory=dict)
    message: str = ""
    newsletter_triggered: bool = False


class ExportAgent(BaseAgent):
    """Déploie le livrable et produit un manifeste universel."""

    @property
    def agent_id(self) -> str:
        return "export"

    @property
    def name(self) -> str:
        return "ExportAI"

    async def run(self, prompt: str, **kwargs: Any) -> str:
        plan = kwargs.get("architect_plan")
        analysis = kwargs.get("analysis")
        generation = kwargs.get("generation")
        preview_html = kwargs.get("preview_html")
        if not isinstance(plan, ArchitectPlan) or not isinstance(analysis, CoreMindAnalysis):
            raise ValueError("architect_plan et analysis requis pour ExportAI")
        if not isinstance(generation, CodeGenerateResult):
            raise ValueError("generation requis pour ExportAI")
        result = await self.export(
            prompt,
            plan=plan,
            analysis=analysis,
            generation=generation,
            preview_html=str(preview_html or ""),
        )
        return result.model_dump_json()

    def _collect_files(
        self,
        generation: CodeGenerateResult,
        resolved_index_html: str,
    ) -> dict[str, str]:
        """index.html = HTML pipeline résolu uniquement (pas generation.code dashboard)."""
        files: dict[str, str] = {}
        if resolved_index_html.strip() and is_usable_preview_html(resolved_index_html):
            files["index.html"] = resolved_index_html.strip()
        if generation.files:
            for f in generation.files:
                if not f.path or not f.content:
                    continue
                path = f.path.strip().lstrip("/").replace("\\", "/").lower()
                if path in ("index.html", "index.htm"):
                    continue
                files[f.path] = f.content
        code = (generation.code or "").strip()
        if code and "index.html" not in files:
            is_html = code.lower().startswith("<!") or "<html" in code[:500].lower()
            if not is_html:
                files.setdefault("src/App.tsx", code)
        return files

    async def export(
        self,
        prompt: str,
        *,
        plan: ArchitectPlan,
        analysis: CoreMindAnalysis,
        generation: CodeGenerateResult,
        assembled_html: str = "",
        preview_html: str = "",
        template_id: str | None = None,
        sector_template: dict[str, Any] | None = None,
        expect_sector_template: bool = False,
        settings: Settings | None = None,
        project_id: str | None = None,
        generation_mode: str | None = None,
        personal_project: bool = False,
        pages_project_slug: str | None = None,
        project_title: str | None = None,
        extension_files: dict[str, str] | None = None,
    ) -> ExportResult:
        resolved = settings or self._settings

        from tools.extension_pipeline import is_extension_project_type

        if (
            plan.project_type == ProjectType.EXTENSION_NAVIGATEUR
            or is_extension_project_type(plan)
        ):
            from tools.extension_pipeline import (
                build_extension_export_manifest,
                build_extension_zip,
                extension_artifact_download_path,
                save_extension_zip_artifact,
            )

            files = extension_files or {
                f.path: f.content
                for f in (generation.files or [])
                if f.path and f.content
            }
            if not files:
                return ExportResult(
                    success=False,
                    provider="zip",
                    message="Aucun fichier extension à exporter.",
                )
            zip_bytes = build_extension_zip(files)
            pid = project_id or slugify_project_name(
                project_title or plan.project_type_label or "extension"
            )
            save_extension_zip_artifact(pid, zip_bytes)
            download_url = extension_artifact_download_path(pid)
            manifest = build_extension_export_manifest(
                project_id=pid,
                project_type_label=plan.project_type_label,
                files=list(files.keys()),
                zip_bytes=len(zip_bytes),
                download_url=download_url,
            )
            return ExportResult(
                success=True,
                provider="zip",
                production_url=None,
                artifact_download_url=download_url,
                manifest=manifest,
                message=f"Extension Chrome prête — télécharger le ZIP ({len(zip_bytes)} octets).",
            )

        base_project_name = slugify_project_name(
            pages_project_slug
            or project_title
            or plan.project_type_label
            or analysis.project_type_label
            or "projet"
        )
        mode = (generation_mode or "client_demo").strip()
        use_dedicated_pages = personal_project and mode == "real_app"
        explicit_stable_pages_slug = bool(
            use_dedicated_pages and (pages_project_slug or "").strip()
        )
        if explicit_stable_pages_slug:
            project_name = slugify_project_name((pages_project_slug or "").strip())
        else:
            project_name = unique_deploy_slug(
                base_project_name,
                project_id=project_id,
            )
        # Phase 4 vitrines Next.js : on publie le scaffold via GitHub (puis Vercel).
        # (Le CLI Vercel n'est pas requis : l'utilisateur connecte Vercel au repo/branche.)
        provider = (
            "github"
            if generation.stack and "vitrine_next" in generation.stack
            else select_export_provider(plan.project_type, prompt)
        )
        html, upload_source, resolved_template_id = resolve_export_html_for_upload(
            assembled_html=assembled_html or None,
            preview_html=preview_html or None,
            generation=generation,
            template_id=template_id,
            sector_template=sector_template,
            expect_sector_template=expect_sector_template,
        )
        log_export_upload_source(
            source=upload_source,
            template_id=resolved_template_id,
            html=html,
        )
        files = self._collect_files(generation, html)
        file_paths = list(files.keys())

        env: dict[str, str] = {
            "APP_ENV": resolved.app_env,
            "PROJECT_TYPE": plan.project_type.value,
        }
        secondary: list[str] = []
        production_url: str | None = None
        github_url: str | None = None
        demo_token: str | None = None
        demo_password: str | None = None
        unlock_url: str | None = None
        message = ""

        title = (
            (project_title or "").strip()
            or plan.project_type_label
            or "Démo CyberForge"
        )

        def _log_export_deploy(slug: str, html_payload: str) -> None:
            size = len(html_payload.encode("utf-8"))
            logger.info(
                "[ExportAI] Déploiement slug=%s html_size=%s bytes",
                slug,
                size,
            )

        async def _deploy_dedicated() -> None:
            nonlocal production_url, provider, message
            deploy_files = dict(files)
            html_candidate = html.strip()
            if html_candidate and is_usable_preview_html(html_candidate):
                deploy_files["index.html"] = html_candidate
            if "index.html" not in deploy_files:
                raise CloudflareExportError(
                    "index.html requis pour un déploiement Pages dédié."
                )
            _log_export_deploy(
                project_name,
                deploy_files.get("index.html", html_candidate),
            )
            production_url = await deploy_dedicated_pages(
                project_slug=project_name,
                files=deploy_files,
                title=title,
            )
            provider = "cloudflare"
            env["PAGES_PROJECT"] = project_name
            env["PAGES_URL"] = production_url
            message = f"Site publié sur Cloudflare Pages — {production_url}"

        async def _deploy_cloudflare() -> None:
            nonlocal production_url, demo_token, demo_password, unlock_url, provider, message
            if not html.strip() or not is_usable_preview_html(html):
                raise CloudflareExportError("HTML premium requis pour Cloudflare Pages.")
            production_url, demo_token, demo_password, unlock_url = await deploy_html_demo(
                html=html,
                title=title,
            )
            _log_export_deploy(pages_token_slug(demo_token or ""), html)
            provider = "cloudflare"
            env["DEMO_TOKEN"] = demo_token or ""
            env["DEMO_PASSWORD"] = demo_password or ""
            message = f"Démo publiée sur Cloudflare — {production_url}"

        try:
            if use_dedicated_pages and resolved.cloudflare_configured:
                await _deploy_dedicated()
            elif provider == "github":
                # publication via GitHub ci-dessous (push_source_to_github)
                message = "Sources prêtes pour Vercel (publication GitHub)…"
            elif provider == "railway" and plain_secret_str(resolved.railway_api_key):
                production_url, railway_id = await deploy_to_railway(
                    project_name=project_name,
                    settings=resolved,
                )
                env["RAILWAY_PROJECT_ID"] = railway_id
                message = f"Projet Railway créé — {production_url}"
            elif resolved.cloudflare_configured:
                await _deploy_cloudflare()
            else:
                raise CloudflareExportError(
                    "Configurez CLOUDFLARE_* ou RAILWAY_API_KEY pour ExportAI."
                )
        except RailwayExportError as exc:
            logger.warning("Railway indisponible (%s), repli Cloudflare", exc)
            message = str(exc)
            if resolved.cloudflare_configured:
                try:
                    await _deploy_cloudflare()
                    message = f"Repli Cloudflare — {production_url}"
                except CloudflareExportError as cf_exc:
                    message = f"{message} ; Cloudflare : {cf_exc}"
            elif not message:
                message = str(exc)
        except CloudflareExportError as exc:
            message = str(exc)
            if (
                provider == "cloudflare"
                and plain_secret_str(resolved.railway_api_key)
                and not production_url
            ):
                try:
                    production_url, railway_id = await deploy_to_railway(
                        project_name=project_name,
                        settings=resolved,
                    )
                    provider = "railway"
                    env["RAILWAY_PROJECT_ID"] = railway_id
                    message = f"Repli Railway — {production_url}"
                except RailwayExportError as rw_exc:
                    message = f"{message} ; Railway : {rw_exc}"

        is_vitrine = bool(generation.stack and "vitrine_next" in generation.stack)

        if plain_secret_str(resolved.github_token) and files:
            try:
                if is_vitrine:
                    vitrines_repo = (
                        resolved.vitrines_github_repo or DEFAULT_VITRINES_REPO
                    ).strip()
                    branch = vitrine_branch_name(project_name)
                    github_url = await push_vitrine_site_to_github(
                        branch_slug=project_name,
                        files=files,
                        settings=resolved,
                        repo=vitrines_repo,
                    )
                    env["VITRINES_REPO"] = vitrines_repo
                    env["VITRINE_BRANCH"] = branch
                else:
                    github_url = await push_source_to_github(
                        project_slug=project_name,
                        files=files,
                        settings=resolved,
                    )
                if github_url:
                    secondary.append("github")
                    env["GITHUB_URL"] = github_url
            except Exception as exc:
                logger.warning("Export GitHub ignoré : %s", exc)

        if provider == "github" and github_url and not production_url:
            production_url = github_url
            if is_vitrine:
                branch = env.get("VITRINE_BRANCH", vitrine_branch_name(project_name))
                repo = env.get("VITRINES_REPO", DEFAULT_VITRINES_REPO)
                message = (
                    f"Vitrine publiée sur {repo} (branche `{branch}`) — "
                    "Vercel peut déployer chaque branche automatiquement."
                )
            else:
                message = "Sources publiées sur GitHub — connectez la branche à Vercel."

        domain_host = None
        if production_url:
            domain_host = urlparse(production_url).netloc

        manifest = build_deploy_manifest(
            project_name=project_name,
            project_type=plan.project_type,
            project_type_label=plan.project_type_label,
            provider=provider,
            domain=domain_host,
            env=env,
            files=file_paths,
            secondary_targets=secondary,
        )

        success = bool(production_url)
        if not message:
            message = "Export terminé." if success else "Export sans URL de production."

        if project_id and github_url:
            maybe_track_cost(project_id, "github", {"requests": 1})
        if project_id and provider == "cloudflare" and production_url:
            maybe_track_cost(project_id, "cloudflare", {"requests": 1})
        if project_id and provider == "railway" and production_url:
            maybe_track_cost(project_id, "railway", {"requests": 1})

        if personal_project and use_dedicated_pages and production_url:
            try:
                import personal_projects_db as pp_db

                pp_row = pp_db.find_personal_project_by_title(title)
                if pp_row:
                    pp_db.update_personal_project(
                        str(pp_row["id"]),
                        production_url=production_url,
                        pages_project_slug=project_name,
                    )
            except Exception as exc:
                logger.warning("Mise à jour projet perso ignorée : %s", exc)

        display_name = (
            (project_title or "").strip()
            or plan.project_type_label
            or analysis.project_type_label
            or project_name
        )

        from routers.notifications import notify

        if success and production_url:
            try:
                await notify(
                    "Projet livré ✅",
                    "project_delivered",
                    "success",
                    f"{display_name} déployé sur {production_url}",
                    project_id,
                    display_name,
                )
            except Exception as exc:
                logger.warning("Notification livraison ignorée : %s", exc)
        elif not success:
            try:
                await notify(
                    "Erreur de déploiement",
                    "deploy_error",
                    "error",
                    message or "Export sans URL de production.",
                    project_id,
                    display_name,
                )
            except Exception as exc:
                logger.warning("Notification erreur déploiement ignorée : %s", exc)

        newsletter_triggered = False
        if success and project_id:
            try:
                from newsletter_router import trigger_welcome_sequence

                await trigger_welcome_sequence(str(project_id))
                newsletter_triggered = True
            except Exception as exc:
                logger.warning(
                    "Newsletter sequence failed (non-blocking): %s",
                    exc,
                )

        return ExportResult(
            success=success,
            provider=provider,
            production_url=production_url,
            github_url=github_url,
            demo_token=demo_token,
            demo_password=demo_password,
            unlock_url=unlock_url,
            manifest=manifest.model_dump(),
            message=message,
            newsletter_triggered=newsletter_triggered,
        )

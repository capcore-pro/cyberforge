"""
Persistance Supabase — projets et générations via PostgREST (httpx).
Utilise SUPABASE_SECRET_KEY côté backend uniquement.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field

from agents.coremind_agent import PROJECT_TYPE_LABELS, CoreMindRunResult, ProjectType
from config import Settings, get_settings, plain_secret_str
from tools.project_title import clean_project_title, short_project_name
from tools.demo_preview_html import build_demo_preview_html
from tools.desktop_zip_export import electron_files_from_generation_files

logger = logging.getLogger(__name__)

PROJECT_LIST_SELECT = (
    "id,title,prompt,project_type,summary,created_at,updated_at,demo_url"
)


class SupabaseErrorDetail(BaseModel):
    """Détail d'une erreur PostgREST (sans secrets)."""

    message: str
    operation: str
    method: str
    url: str
    status_code: int | None = None
    response_body: str | None = None
    hint: str | None = None
    configured: bool = True
    has_secret_key: bool = False
    has_anon_key: bool = False


class SupabaseStoreError(Exception):
    """Erreur d'accès Supabase."""

    def __init__(
        self,
        message: str,
        *,
        detail: SupabaseErrorDetail | None = None,
    ) -> None:
        super().__init__(message)
        self.detail = detail or SupabaseErrorDetail(
            message=message,
            operation="unknown",
            method="?",
            url="",
        )

    def to_http_detail(self) -> dict[str, Any]:
        return self.detail.model_dump(exclude_none=True)


class PersistenceResult(BaseModel):
    """Identifiants enregistrés après une génération réussie."""

    project_id: str
    generation_id: str
    storage: str = "supabase"


class ProjectRow(BaseModel):
    id: str
    title: str
    prompt: str
    project_type: str
    summary: str | None = None
    created_at: str
    updated_at: str
    demo_url: str | None = None
    generation_count: int = 0
    latest_model: str | None = None
    latest_estimated_cost_usd: float | None = None
    preview_html: str | None = None


class GenerationRow(BaseModel):
    id: str
    project_id: str
    prompt: str
    project_type: str
    model: str
    provider: str
    complexity: str
    complexity_score: int
    duration_ms: int
    estimated_cost_usd: float
    code: str
    files: list[dict[str, str]]
    stack: list[str]
    analysis: dict[str, Any]
    generation_summary: str | None = None
    planned_models: list[str] = Field(default_factory=list)
    preview_html: str | None = None
    created_at: str


class ProjectDetailResponse(BaseModel):
    project: ProjectRow
    generations: list[GenerationRow]


class SupabaseStore:
    """Client PostgREST minimal pour projects / generations."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def is_configured(self) -> bool:
        return self._settings.supabase_configured

    def connection_diagnostics(self) -> dict[str, Any]:
        """Indicateurs de config (sans exposer les clés)."""
        url = self._url
        secret = self._secret_key
        anon = self._anon_key
        return {
            "supabase_url_set": bool(url),
            "supabase_secret_key_set": bool(secret),
            "supabase_anon_key_set": bool(anon),
            "rest_base": f"{url}/rest/v1" if url else None,
            "secret_key_prefix": secret[:12] + "…" if len(secret) > 12 else None,
            "anon_key_prefix": anon[:12] + "…" if len(anon) > 12 else None,
        }

    @property
    def _url(self) -> str | None:
        raw = self._settings.supabase_url
        if not raw:
            return None
        cleaned = raw.strip().rstrip("/")
        return cleaned or None

    @property
    def _secret_key(self) -> str:
        return plain_secret_str(self._settings.supabase_secret_key)

    @property
    def _anon_key(self) -> str:
        return plain_secret_str(self._settings.supabase_anon_key)

    def _headers(self, prefer: str | None = None) -> dict[str, str]:
        secret = self._secret_key
        if not secret:
            raise SupabaseStoreError(
                "SUPABASE_SECRET_KEY manquant ou invalide (SecretStr non résolu)."
            )
        # sb_secret_* : apikey et Bearer doivent être la même clé (pas un JWT).
        # service_role JWT : apikey = anon, Authorization = service_role.
        if secret.startswith("sb_secret_"):
            api_key = secret
        else:
            api_key = self._anon_key or secret
        headers = {
            "apikey": api_key,
            "Authorization": f"Bearer {secret}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Profile": "public",
            "Content-Profile": "public",
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    async def save_generation(
        self,
        prompt: str,
        project_type: ProjectType,
        run_result: CoreMindRunResult,
    ) -> PersistenceResult:
        """Crée ou réutilise un projet, puis enregistre la génération."""
        if not self.is_configured():
            raise SupabaseStoreError(
                "Supabase non configuré : SUPABASE_URL et SUPABASE_SECRET_KEY requis."
            )

        trimmed = prompt.strip()
        project_id = await self._find_or_create_project(
            trimmed, project_type, run_result
        )
        generation_id = await self._insert_generation(
            project_id, trimmed, project_type, run_result
        )
        await self._touch_project(project_id)
        return PersistenceResult(project_id=project_id, generation_id=generation_id)

    async def save_pipeline_v2_deploy(
        self,
        *,
        prompt: str,
        project_type: str,
        client_name: str,
        demo_url: str,
        html: str,
        duration_ms: int = 0,
        estimated_cost_usd: float = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
        generation_id: str | None = None,
        electron_files: dict[str, str] | None = None,
    ) -> PersistenceResult | None:
        """Enregistre un run pipeline v2 (brief → generate → deploy) dans Supabase."""
        if not self.is_configured():
            return None

        trimmed = prompt.strip()
        pt = (project_type or "vitrine_next").strip()
        title = clean_project_title(client_name.strip()) or _title_from_prompt(trimmed)
        url = (demo_url or "").strip() or None
        code = (html or "").strip()
        files: list[dict[str, str]] = []
        if code:
            files.append({"path": "index.html", "content": code[:15000]})
        if isinstance(electron_files, dict):
            for name in ("main.js", "preload.js", "package.json", "instructions_build.md"):
                content = str(electron_files.get(name) or "").strip()
                if content:
                    files.append({"path": name, "content": content[:50000]})

        async with httpx.AsyncClient(timeout=30.0) as client:
            find_resp = await client.get(
                f"{self._rest_url()}/projects",
                headers=self._headers(),
                params={
                    "prompt": f"eq.{trimmed}",
                    "project_type": f"eq.{pt}",
                    "select": "id",
                    "limit": "1",
                },
            )
            _raise_for_status(
                find_resp,
                "find_project_v2",
                "GET",
                f"{self._rest_url()}/projects",
                self,
            )
            existing = find_resp.json()
            if isinstance(existing, list) and existing:
                project_id = str(existing[0]["id"])
                patch: dict[str, Any] = {
                    "updated_at": datetime.now(UTC).isoformat(),
                }
                if url:
                    patch["demo_url"] = url
                if title:
                    patch["title"] = title
                await client.patch(
                    f"{self._rest_url()}/projects",
                    headers=self._headers(),
                    params={"id": f"eq.{project_id}"},
                    json=patch,
                )
            else:
                create_resp = await client.post(
                    f"{self._rest_url()}/projects",
                    headers=self._headers("return=representation"),
                    json={
                        "title": title,
                        "prompt": trimmed,
                        "project_type": pt,
                        "summary": "Pipeline CyberForge v2",
                        "demo_url": url,
                    },
                )
                _raise_for_status(
                    create_resp,
                    "create_project_v2",
                    "POST",
                    f"{self._rest_url()}/projects",
                    self,
                )
                created = create_resp.json()
                if isinstance(created, list) and created:
                    project_id = str(created[0]["id"])
                elif isinstance(created, dict) and created.get("id"):
                    project_id = str(created["id"])
                else:
                    raise SupabaseStoreError("Création projet v2 sans identifiant.")

            analysis: dict[str, Any] = {
                "summary": "Pipeline v2",
                "agent_id": "cyberforge",
            }
            if generation_id:
                analysis["generation_stream_id"] = generation_id
            if isinstance(electron_files, dict) and electron_files:
                analysis["desktop_package"] = True

            gen_payload = {
                "project_id": project_id,
                "prompt": trimmed,
                "project_type": pt,
                "model": "cyberforge-v2",
                "provider": "cyberforge",
                "complexity": "moyenne",
                "complexity_score": 5,
                "duration_ms": max(0, int(duration_ms or 0)),
                "estimated_cost_usd": float(estimated_cost_usd or 0),
                "input_tokens": max(0, int(input_tokens or 0)),
                "output_tokens": max(0, int(output_tokens or 0)),
                "total_tokens": max(0, int(total_tokens or 0)),
                "code": code[:50000],
                "files": files,
                "stack": ["html"],
                "analysis": analysis,
                "generation_summary": "Génération HTML pipeline v2",
                "planned_models": ["brief-ai", "generator-ai", "deploy-ai"],
                "preview_html": code[:50000] if code else None,
            }
            gen_resp = await client.post(
                f"{self._rest_url()}/generations",
                headers=self._headers("return=representation"),
                json=gen_payload,
            )
            _raise_for_status(
                gen_resp,
                "insert_generation_v2",
                "POST",
                f"{self._rest_url()}/generations",
                self,
            )
            gen_data = gen_resp.json()
            if isinstance(gen_data, list) and gen_data:
                generation_id = str(gen_data[0]["id"])
            elif isinstance(gen_data, dict) and gen_data.get("id"):
                generation_id = str(gen_data["id"])
            else:
                raise SupabaseStoreError("Insertion génération v2 sans identifiant.")

        return PersistenceResult(project_id=project_id, generation_id=generation_id)

    async def list_projects(self, limit: int = 50) -> list[ProjectRow]:
        if not self.is_configured():
            return []

        url = f"{self._rest_url()}/projects"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                projects_resp = await client.get(
                    url,
                    headers=self._headers(),
                    params={
                        "select": PROJECT_LIST_SELECT,
                        "order": "updated_at.desc",
                        "limit": str(limit),
                    },
                )
            except httpx.HTTPError as exc:
                _raise_transport_error(exc, "list_projects", "GET", url, self)

            _raise_for_status(projects_resp, "list_projects", "GET", url, self)
            projects = projects_resp.json()
            if not isinstance(projects, list):
                return []

            result: list[ProjectRow] = []
            for row in projects:
                project_id = str(row["id"])
                title = clean_project_title(str(row["title"]))
                count, latest_model, latest_cost, preview_html = (
                    await self._project_card_stats(client, project_id, title)
                )
                demo_url = (row.get("demo_url") or "").strip() or None
                if not demo_url:
                    demo_url = await self._resolve_demo_url_for_project(
                        client, project_id
                    )
                result.append(
                    ProjectRow(
                        id=project_id,
                        title=title,
                        prompt=str(row["prompt"]),
                        project_type=str(row["project_type"]),
                        summary=row.get("summary"),
                        created_at=str(row["created_at"]),
                        updated_at=str(row["updated_at"]),
                        demo_url=demo_url,
                        generation_count=count,
                        latest_model=latest_model,
                        latest_estimated_cost_usd=latest_cost,
                        preview_html=preview_html,
                    )
                )
            return result

    async def get_project(self, project_id: str) -> ProjectDetailResponse | None:
        if not self.is_configured():
            return None

        async with httpx.AsyncClient(timeout=30.0) as client:
            project_resp = await client.get(
                f"{self._rest_url()}/projects",
                headers=self._headers(),
                params={"id": f"eq.{project_id}", "select": PROJECT_LIST_SELECT},
            )
            _raise_for_status(
                project_resp,
                "get_project",
                "GET",
                f"{self._rest_url()}/projects",
                self,
            )
            rows = project_resp.json()
            if not rows:
                return None

            row = rows[0]
            title = clean_project_title(str(row["title"]))
            count, latest_model, latest_cost, preview_html = (
                await self._project_card_stats(client, project_id, title)
            )
            demo_url = (row.get("demo_url") or "").strip() or None
            if not demo_url:
                demo_url = await self._resolve_demo_url_for_project(
                    client, project_id
                )
            project = ProjectRow(
                id=str(row["id"]),
                title=title,
                prompt=str(row["prompt"]),
                project_type=str(row["project_type"]),
                summary=row.get("summary"),
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
                demo_url=demo_url,
                generation_count=count,
                latest_model=latest_model,
                latest_estimated_cost_usd=latest_cost,
                preview_html=preview_html,
            )

            gens_resp = await client.get(
                f"{self._rest_url()}/generations",
                headers=self._headers(),
                params={
                    "project_id": f"eq.{project_id}",
                    "select": "*",
                    "order": "created_at.desc",
                },
            )
            _raise_for_status(
                gens_resp,
                "list_generations",
                "GET",
                f"{self._rest_url()}/generations",
                self,
            )
            generations = [
                _generation_from_row(g)
                for g in gens_resp.json()
                if isinstance(g, dict)
            ]
            return ProjectDetailResponse(project=project, generations=generations)

    async def delete_project(self, project_id: str) -> bool:
        """Supprime un projet (les générations sont supprimées en cascade)."""
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.delete(
                f"{self._rest_url()}/projects",
                headers=self._headers("return=minimal"),
                params={"id": f"eq.{project_id}"},
            )
            _raise_for_status(
                resp,
                "delete_project",
                "DELETE",
                f"{self._rest_url()}/projects",
                self,
            )
        return True

    async def update_project_metadata(
        self,
        project_id: str,
        *,
        title: str | None = None,
        prompt: str | None = None,
    ) -> ProjectRow | None:
        """Met à jour le titre et/ou le prompt d'un projet."""
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        patch: dict[str, Any] = {"updated_at": datetime.now(UTC).isoformat()}
        if title is not None:
            clean = clean_project_title(title.strip())
            if not clean:
                raise SupabaseStoreError("Le titre du projet ne peut pas être vide.")
            patch["title"] = clean
        if prompt is not None:
            trimmed = prompt.strip()
            if len(trimmed) < 3:
                raise SupabaseStoreError("Le prompt doit contenir au moins 3 caractères.")
            patch["prompt"] = trimmed

        if len(patch) == 1:
            detail = await self.get_project(project_id)
            return detail.project if detail else None

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(
                f"{self._rest_url()}/projects",
                headers=self._headers("return=representation"),
                params={"id": f"eq.{project_id}"},
                json=patch,
            )
            _raise_for_status(
                resp,
                "update_project_metadata",
                "PATCH",
                f"{self._rest_url()}/projects",
                self,
            )
            rows = resp.json()
            if not isinstance(rows, list) or not rows:
                return None
            row = rows[0]
            return ProjectRow(
                id=str(row["id"]),
                title=clean_project_title(str(row["title"])),
                prompt=str(row["prompt"]),
                project_type=str(row["project_type"]),
                summary=row.get("summary"),
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
                demo_url=(row.get("demo_url") or "").strip() or None,
            )

    async def duplicate_project(self, project_id: str) -> ProjectDetailResponse | None:
        """Duplique un projet et sa dernière génération."""
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        detail = await self.get_project(project_id)
        if detail is None:
            return None

        source = detail.project
        copy_title = clean_project_title(f"Copie de {source.title}")
        now = datetime.now(UTC).isoformat()

        async with httpx.AsyncClient(timeout=30.0) as client:
            create_resp = await client.post(
                f"{self._rest_url()}/projects",
                headers=self._headers("return=representation"),
                json={
                    "title": copy_title,
                    "prompt": source.prompt,
                    "project_type": source.project_type,
                    "summary": source.summary,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            _raise_for_status(
                create_resp,
                "duplicate_project",
                "POST",
                f"{self._rest_url()}/projects",
                self,
            )
            created_rows = create_resp.json()
            if not isinstance(created_rows, list) or not created_rows:
                raise SupabaseStoreError("Duplication projet sans identifiant retourné.")
            new_id = str(created_rows[0]["id"])

            if detail.generations:
                latest = detail.generations[0]
                gen_payload = {
                    "project_id": new_id,
                    "prompt": latest.prompt,
                    "project_type": latest.project_type,
                    "model": latest.model,
                    "provider": latest.provider,
                    "complexity": latest.complexity,
                    "complexity_score": latest.complexity_score,
                    "duration_ms": latest.duration_ms,
                    "estimated_cost_usd": latest.estimated_cost_usd,
                    "code": latest.code,
                    "files": latest.files,
                    "stack": latest.stack,
                    "analysis": latest.analysis,
                    "generation_summary": latest.generation_summary,
                    "planned_models": latest.planned_models,
                    "preview_html": latest.preview_html,
                    "created_at": now,
                }
                gen_resp = await client.post(
                    f"{self._rest_url()}/generations",
                    headers=self._headers("return=representation"),
                    json=gen_payload,
                )
                _raise_for_status(
                    gen_resp,
                    "duplicate_generation",
                    "POST",
                    f"{self._rest_url()}/generations",
                    self,
                )

        return await self.get_project(new_id)

    async def _find_or_create_project(
        self,
        prompt: str,
        project_type: ProjectType,
        run_result: CoreMindRunResult,
    ) -> str:
        type_value = project_type.value
        title = _title_from_prompt(prompt)

        async with httpx.AsyncClient(timeout=30.0) as client:
            find_resp = await client.get(
                f"{self._rest_url()}/projects",
                headers=self._headers(),
                params={
                    "prompt": f"eq.{prompt}",
                    "project_type": f"eq.{type_value}",
                    "select": "id",
                    "limit": "1",
                },
            )
            _raise_for_status(
                find_resp,
                "find_project",
                "GET",
                f"{self._rest_url()}/projects",
                self,
            )
            existing = find_resp.json()
            if isinstance(existing, list) and existing:
                return str(existing[0]["id"])

            create_resp = await client.post(
                f"{self._rest_url()}/projects",
                headers=self._headers("return=representation"),
                json={
                    "title": title,
                    "prompt": prompt,
                    "project_type": type_value,
                    "summary": run_result.analysis.summary,
                },
            )
            _raise_for_status(
                create_resp,
                "create_project",
                "POST",
                f"{self._rest_url()}/projects",
                self,
            )
            created = create_resp.json()
            if isinstance(created, list) and created:
                return str(created[0]["id"])
            if isinstance(created, dict) and created.get("id"):
                return str(created["id"])
            raise SupabaseStoreError("Création projet sans identifiant retourné.")

    async def _insert_generation(
        self,
        project_id: str,
        prompt: str,
        project_type: ProjectType,
        run_result: CoreMindRunResult,
    ) -> str:
        gen = run_result.generation
        metrics = run_result.metrics
        from tools.generation_sources import normalize_generation_sources

        files = [{"path": f.path, "content": f.content} for f in gen.files]
        norm_files, norm_code = normalize_generation_sources(files, gen.code)
        project_title = _title_from_prompt(prompt)
        from tools.export_html_resolve import force_finalize_preview_from_assembled
        from tools.html_markdown import strip_markdown_code_fences

        sector_tpl = getattr(run_result, "sector_template", None)
        sector_html = None
        if isinstance(sector_tpl, dict):
            sector_html = sector_tpl.get("html") or sector_tpl.get("html_raw")

        assembled_raw = strip_markdown_code_fences(
            str(getattr(run_result, "assembled_html", None) or "")
        )
        if assembled_raw.strip():
            from tools.demo_preview_gate import prepare_internal_app_preview_html

            preview_html = (
                prepare_internal_app_preview_html(assembled_raw) or assembled_raw
            )
        else:
            preview_html, _assembled = force_finalize_preview_from_assembled(
                state_assembled_html=None,
                preview_html=run_result.preview_html,
                assembled_html=getattr(run_result, "assembled_html", None),
                sector_template_html=sector_html,
                generation=gen,
                title=PROJECT_TYPE_LABELS.get(project_type, project_type.value),
                user_prompt=prompt,
            )
            if not preview_html:
                from tools.demo_pipeline import build_client_demo_document

                document = await build_client_demo_document(
                    prompt,
                    project_type_label=PROJECT_TYPE_LABELS.get(
                        project_type, project_type.value
                    ),
                    project_id=project_id,
                )
                preview_html, _assembled = force_finalize_preview_from_assembled(
                    state_assembled_html=document.html,
                    preview_html=document.html,
                    assembled_html=document.html,
                    sector_template_html=None,
                    generation=None,
                    title=PROJECT_TYPE_LABELS.get(
                        project_type, project_type.value
                    ),
                    user_prompt=prompt,
                )

        analysis_payload: dict[str, Any] = run_result.analysis.model_dump()
        # Ajoute les schémas générés (DatabaseAI/AuthAI/PaymentAI) dans le JSON analysis
        # pour qu'ils soient persistés sans migration SQL.
        if isinstance(getattr(run_result, "database_schema", None), dict):
            analysis_payload["database_schema"] = getattr(run_result, "database_schema")
        if isinstance(getattr(run_result, "auth_schema", None), dict):
            analysis_payload["auth_schema"] = getattr(run_result, "auth_schema")
        if isinstance(getattr(run_result, "payment_config", None), dict):
            analysis_payload["payment_config"] = getattr(run_result, "payment_config")

        payload = {
            "project_id": project_id,
            "prompt": prompt,
            "project_type": project_type.value,
            "model": metrics.model,
            "provider": metrics.provider,
            "complexity": metrics.complexity.value,
            "complexity_score": metrics.complexity_score,
            "duration_ms": metrics.duration_ms,
            "estimated_cost_usd": metrics.estimated_cost_usd,
            "code": gen.code,
            "files": files,
            "stack": gen.stack,
            "analysis": analysis_payload,
            "generation_summary": gen.summary,
            "planned_models": run_result.planned_models,
            "preview_html": preview_html,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._rest_url()}/generations",
                headers=self._headers("return=representation"),
                json=payload,
            )
            _raise_for_status(
                resp,
                "insert_generation",
                "POST",
                f"{self._rest_url()}/generations",
                self,
            )
            data = resp.json()
            if isinstance(data, list) and data:
                return str(data[0]["id"])
            if isinstance(data, dict) and data.get("id"):
                return str(data["id"])
            raise SupabaseStoreError("Insertion génération sans identifiant.")

    async def resolve_public_demo_url(self, generation_or_project_id: str) -> str | None:
        """URL publique depuis projects.demo_url (id = project ou generation)."""
        if not self.is_configured():
            return None
        needle = (generation_or_project_id or "").strip()
        if not needle:
            return None

        detail = await self.get_project(needle)
        if detail:
            url = (detail.project.demo_url or "").strip()
            if url:
                return url

        async with httpx.AsyncClient(timeout=30.0) as client:
            gen_resp = await client.get(
                f"{self._rest_url()}/generations",
                headers=self._headers(),
                params={
                    "id": f"eq.{needle}",
                    "select": "project_id",
                    "limit": "1",
                },
            )
            if gen_resp.status_code >= 400:
                return None
            rows = gen_resp.json()
            if not isinstance(rows, list) or not rows:
                return None
            project_id = str(rows[0].get("project_id") or "").strip()
            if not project_id:
                return None

        project_detail = await self.get_project(project_id)
        if not project_detail:
            return None
        return (project_detail.project.demo_url or "").strip() or None

    async def _resolve_demo_url_for_project(
        self,
        client: httpx.AsyncClient,
        project_id: str,
    ) -> str | None:
        """URL Cloudflare depuis la dernière génération liée à une démo (fallback)."""
        latest_resp = await client.get(
            f"{self._rest_url()}/generations",
            headers=self._headers(),
            params={
                "project_id": f"eq.{project_id}",
                "select": "id",
                "order": "created_at.desc",
                "limit": "1",
            },
        )
        if latest_resp.status_code >= 400:
            return None
        rows = latest_resp.json()
        if not isinstance(rows, list) or not rows:
            return None
        generation_id = str(rows[0].get("id") or "")
        if not generation_id:
            return None

        from db.demos_store import get_demos_store

        demo_store = get_demos_store()
        if not demo_store.is_configured():
            return None
        demo = await demo_store.find_by_generation_id(generation_id)
        if demo is None:
            return None
        url = (demo.payload.cloudflare_url or "").strip()
        return url or None

    async def _touch_project(self, project_id: str) -> None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.patch(
                f"{self._rest_url()}/projects",
                headers=self._headers(),
                params={"id": f"eq.{project_id}"},
                json={"updated_at": datetime.now(UTC).isoformat()},
            )

    async def get_editor_html(self, project_id: str) -> dict[str, Any] | None:
        """HTML éditable de la dernière génération d'un projet."""
        detail = await self.get_project(project_id)
        if detail is None or not detail.generations:
            return None
        gen = detail.generations[0]
        html = (gen.preview_html or gen.code or "").strip()
        if not html:
            return None
        electron_files = electron_files_from_generation_files(
            gen.files if isinstance(gen.files, list) else None,
        )
        return {
            "generation_id": gen.id,
            "html": html,
            "demo_url": detail.project.demo_url,
            "project_title": detail.project.title,
            "project_type": detail.project.project_type,
            "electron_files": electron_files,
            "is_desktop": detail.project.project_type == "application_desktop",
        }

    async def save_editor_html(
        self,
        project_id: str,
        generation_id: str,
        html: str,
        *,
        html_before: str | None = None,
        edit_type: str = "manual",
    ) -> None:
        """Persiste le HTML modifié sur la génération + historique éditeur."""
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        trimmed = html.strip()
        if not trimmed:
            raise SupabaseStoreError("HTML vide.")

        detail = await self.get_project(project_id)
        if detail is None:
            raise SupabaseStoreError("Projet introuvable.")

        gen_ids = {g.id for g in detail.generations}
        if generation_id not in gen_ids:
            raise SupabaseStoreError("Génération introuvable pour ce projet.")

        now = datetime.now(UTC).isoformat()
        current_gen = next(g for g in detail.generations if g.id == generation_id)
        edit_count = 0
        async with httpx.AsyncClient(timeout=60.0) as client:
            gen_resp = await client.get(
                f"{self._rest_url()}/generations",
                headers=self._headers(),
                params={
                    "id": f"eq.{generation_id}",
                    "select": "edit_count",
                    "limit": "1",
                },
            )
            if gen_resp.status_code < 400:
                rows = gen_resp.json()
                if isinstance(rows, list) and rows:
                    try:
                        edit_count = int(rows[0].get("edit_count") or 0)
                    except (TypeError, ValueError):
                        edit_count = 0

            patch_resp = await client.patch(
                f"{self._rest_url()}/generations",
                headers=self._headers("return=representation"),
                params={"id": f"eq.{generation_id}"},
                json={
                    "code": trimmed,
                    "preview_html": trimmed,
                    "edited_html": trimmed,
                    "last_edited_at": now,
                    "edit_count": edit_count + 1,
                },
            )
            _raise_for_status(
                patch_resp,
                "save_editor_html",
                "PATCH",
                f"{self._rest_url()}/generations",
                self,
            )

            history_body = {
                "project_id": project_id,
                "generation_id": generation_id,
                "html_before": html_before or current_gen.preview_html or current_gen.code,
                "html_after": trimmed,
                "edit_type": edit_type,
            }
            hist_resp = await client.post(
                f"{self._rest_url()}/editor_history",
                headers=self._headers(),
                json=history_body,
            )
            if hist_resp.status_code >= 400:
                logger.warning(
                    "editor_history insert ignored: %s %s",
                    hist_resp.status_code,
                    hist_resp.text[:300],
                )

            await client.patch(
                f"{self._rest_url()}/projects",
                headers=self._headers(),
                params={"id": f"eq.{project_id}"},
                json={"updated_at": now},
            )

    async def update_project_demo_url(self, project_id: str, demo_url: str) -> None:
        """Met à jour l'URL publique du projet."""
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")
        url = demo_url.strip().rstrip("/")
        if not url:
            raise SupabaseStoreError("URL invalide.")
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(
                f"{self._rest_url()}/projects",
                headers=self._headers(),
                params={"id": f"eq.{project_id}"},
                json={
                    "demo_url": url,
                    "updated_at": datetime.now(UTC).isoformat(),
                },
            )
            _raise_for_status(
                resp,
                "update_project_demo_url",
                "PATCH",
                f"{self._rest_url()}/projects",
                self,
            )

    async def _project_card_stats(
        self,
        client: httpx.AsyncClient,
        project_id: str,
        project_title: str,
    ) -> tuple[int, str | None, float | None, str | None]:
        """Compte les générations et récupère aperçu / coût du dernier run."""
        count_headers = {**self._headers(), "Prefer": "count=exact"}
        count_resp = await client.get(
            f"{self._rest_url()}/generations",
            headers=count_headers,
            params={
                "project_id": f"eq.{project_id}",
                "select": "id",
            },
        )
        count = 0
        if count_resp.status_code < 400:
            content_range = count_resp.headers.get("content-range", "")
            if "/" in content_range:
                try:
                    count = int(content_range.split("/")[-1])
                except ValueError:
                    count = 0
            else:
                rows = count_resp.json()
                count = len(rows) if isinstance(rows, list) else 0

        latest_resp = await client.get(
            f"{self._rest_url()}/generations",
            headers=self._headers(),
            params={
                "project_id": f"eq.{project_id}",
                "select": "model,estimated_cost_usd,preview_html,code,files",
                "order": "created_at.desc",
                "limit": "1",
            },
        )
        if latest_resp.status_code >= 400:
            return count, None, None, None

        rows = latest_resp.json()
        if not isinstance(rows, list) or not rows:
            return count, None, None, None

        latest = rows[0]
        model = str(latest.get("model") or "") or None
        cost_raw = latest.get("estimated_cost_usd")
        cost = float(cost_raw) if cost_raw is not None else None

        stored_preview = latest.get("preview_html")
        files = latest.get("files") if isinstance(latest.get("files"), list) else []
        code = latest.get("code") if isinstance(latest.get("code"), str) else None
        preview = _resolve_preview_html(
            stored_preview if isinstance(stored_preview, str) else None,
            files,
            code,
            project_title,
        )
        return count, model, cost, preview

    async def save_openhands_correction(
        self,
        project_id: str,
        *,
        iterations: int,
        issues_found: list[Any],
        corrections_applied: list[Any],
        quality_score: float,
        report: dict[str, Any],
        redeployed: bool = False,
        deploy_url: str | None = None,
    ) -> dict[str, Any] | None:
        """Persiste un rapport OpenHands (mode Debug)."""
        if not self.is_configured():
            raise SupabaseStoreError("Supabase non configuré.")

        body: dict[str, Any] = {
            "project_id": project_id.strip(),
            "iterations": max(0, int(iterations)),
            "issues_found": issues_found,
            "corrections_applied": corrections_applied,
            "quality_score": float(quality_score),
            "report": report,
            "redeployed": bool(redeployed),
        }
        if deploy_url:
            body["deploy_url"] = deploy_url.strip()
        url = f"{self._rest_url()}/openhands_corrections"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                headers=self._headers("return=representation"),
                json=body,
            )
            if resp.status_code >= 400:
                logger.warning(
                    "openhands_corrections insert ignored: %s %s",
                    resp.status_code,
                    resp.text[:300],
                )
                return None
            rows = resp.json()
            if isinstance(rows, list) and rows:
                return rows[0]
            if isinstance(rows, dict):
                return rows
            return None

    async def get_latest_openhands_correction(
        self,
        project_id: str,
    ) -> dict[str, Any] | None:
        """Dernier rapport OpenHands pour un projet."""
        if not self.is_configured() or not project_id.strip():
            return None

        url = f"{self._rest_url()}/openhands_corrections"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers=self._headers(),
                params={
                    "project_id": f"eq.{project_id.strip()}",
                    "order": "created_at.desc",
                    "limit": "1",
                },
            )
            if resp.status_code >= 400:
                logger.warning(
                    "openhands_corrections read failed: %s %s",
                    resp.status_code,
                    resp.text[:300],
                )
                return None
            rows = resp.json()
            if isinstance(rows, list) and rows:
                return rows[0]
            return None

    def _rest_url(self) -> str:
        if not self._url:
            raise SupabaseStoreError(
                "SUPABASE_URL manquant.",
                detail=SupabaseErrorDetail(
                    message="SUPABASE_URL manquant.",
                    operation="rest_url",
                    method="?",
                    url="",
                    configured=False,
                ),
            )
        return f"{self._url.rstrip('/')}/rest/v1"


def _safe_response_body(response: httpx.Response, limit: int = 2000) -> str:
    try:
        text = response.text
    except Exception as exc:
        return f"<impossible de lire le corps: {exc}>"
    return text[:limit] if len(text) > limit else text


def _raise_for_status(
    response: httpx.Response,
    operation: str,
    method: str,
    url: str,
    store: SupabaseStore,
) -> None:
    if response.status_code < 400:
        return

    body = _safe_response_body(response)
    diag = store.connection_diagnostics()
    message = f"Supabase {operation} échoué — HTTP {response.status_code}"
    detail = SupabaseErrorDetail(
        message=message,
        operation=operation,
        method=method,
        url=url,
        status_code=response.status_code,
        response_body=body,
        hint=_hint_for_status(response.status_code, body),
        configured=store.is_configured(),
        has_secret_key=diag.get("supabase_secret_key_set", False),
        has_anon_key=diag.get("supabase_anon_key_set", False),
    )
    logger.error(
        "%s | %s %s | status=%s | body=%s | diag=%s",
        message,
        method,
        url,
        response.status_code,
        body,
        diag,
    )
    raise SupabaseStoreError(message, detail=detail)


def _raise_transport_error(
    exc: Exception,
    operation: str,
    method: str,
    url: str,
    store: SupabaseStore,
) -> None:
    diag = store.connection_diagnostics()
    message = f"Supabase {operation} — erreur réseau: {exc}"
    detail = SupabaseErrorDetail(
        message=message,
        operation=operation,
        method=method,
        url=url,
        response_body=str(exc),
        hint=(
            "DNS / réseau : vérifiez SUPABASE_URL (copie exacte depuis le dashboard), "
            "la connexion Internet, et l'absence de faute de frappe dans le hostname."
        ),
        configured=store.is_configured(),
        has_secret_key=diag.get("supabase_secret_key_set", False),
        has_anon_key=diag.get("supabase_anon_key_set", False),
    )
    logger.exception(
        "%s | %s %s | diag=%s",
        message,
        method,
        url,
        diag,
    )
    raise SupabaseStoreError(message, detail=detail) from exc


def _hint_for_status(status: int, body: str) -> str:
    lower = body.lower()
    if status == 401:
        return (
            "Clé refusée : utilisez SUPABASE_SECRET_KEY (service_role ou sb_secret_) "
            "et SUPABASE_ANON_KEY pour apikey."
        )
    if status == 404:
        if "relation" in lower and "does not exist" in lower:
            return (
                "PostgREST ne voit pas la table : exécutez la migration SQL, "
                "schéma public, puis Settings → API → Reload schema dans Supabase."
            )
        if "requested path" in lower or "could not find" in lower:
            return (
                "URL Supabase incorrecte : SUPABASE_URL doit être "
                "https://<ref>.supabase.co (sans /rest/v1)."
            )
        return (
            "HTTP 404 PostgREST (pas FastAPI). La route GET /api/projects est bien "
            "enregistrée ; vérifiez SUPABASE_URL et l'exposition des tables."
        )
    if status == 403:
        return "Accès refusé (RLS) : le backend doit utiliser la clé service_role."
    if status >= 500:
        return "Erreur serveur Supabase — réessayez plus tard."
    return "Consultez response_body pour le détail PostgREST."


def _title_from_prompt(prompt: str, max_len: int = 50) -> str:
    # Nom court (max 3 mots) — meilleur rendu dans la sidebar / fiche projet.
    return short_project_name(prompt, max_words=3, max_len=max_len)


def _resolve_preview_html(
    stored: str | None,
    files: list[Any],
    code: str | None,
    title: str,
) -> str | None:
    from tools.generation_sources import is_usable_preview_html, normalize_generation_sources
    from tools.html_markdown import strip_markdown_code_fences

    if stored and stored.strip() and is_usable_preview_html(stored):
        return stored.strip()
    code_clean = strip_markdown_code_fences(str(code or ""))
    if code_clean and is_usable_preview_html(code_clean):
        from tools.demo_preview_gate import prepare_internal_app_preview_html

        return prepare_internal_app_preview_html(code_clean)
    normalized_files = [
        {"path": str(f["path"]), "content": str(f["content"])}
        for f in files
        if isinstance(f, dict) and f.get("path") is not None
    ]
    norm_files, norm_code = normalize_generation_sources(normalized_files, code)
    if not norm_files and not norm_code:
        return None
    try:
        return build_demo_preview_html(norm_files, title=title, code=norm_code)
    except Exception:
        logger.exception("Échec génération aperçu HTML pour projet %s", title)
        return None


def _generation_from_row(row: dict[str, Any]) -> GenerationRow:
    files = row.get("files") or []
    code = str(row.get("code") or "")
    stored = row.get("preview_html")
    preview = _resolve_preview_html(
        stored if isinstance(stored, str) else None,
        files if isinstance(files, list) else [],
        code,
        "Démo CyberForge",
    )
    return GenerationRow(
        id=str(row["id"]),
        project_id=str(row["project_id"]),
        prompt=str(row["prompt"]),
        project_type=str(row["project_type"]),
        model=str(row["model"]),
        provider=str(row["provider"]),
        complexity=str(row["complexity"]),
        complexity_score=int(row["complexity_score"]),
        duration_ms=int(row["duration_ms"]),
        estimated_cost_usd=float(row["estimated_cost_usd"]),
        code=str(row["code"]),
        files=row.get("files") or [],
        stack=row.get("stack") or [],
        analysis=row.get("analysis") or {},
        generation_summary=row.get("generation_summary"),
        planned_models=row.get("planned_models") or [],
        preview_html=preview,
        created_at=str(row["created_at"]),
    )


_store: SupabaseStore | None = None


def get_supabase_store() -> SupabaseStore:
    global _store
    if _store is None:
        _store = SupabaseStore(get_settings())
    return _store


def reset_supabase_store() -> None:
    """Réinitialise le client après rechargement de la config."""
    global _store
    _store = None

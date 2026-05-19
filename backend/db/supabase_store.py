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

from agents.coremind_agent import CoreMindRunResult, ProjectType
from config import Settings, get_settings

logger = logging.getLogger(__name__)


class SupabaseStoreError(Exception):
    """Erreur d'accès Supabase."""


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
    generation_count: int = 0
    latest_model: str | None = None


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
    created_at: str


class ProjectDetailResponse(BaseModel):
    project: ProjectRow
    generations: list[GenerationRow]


class SupabaseStore:
    """Client PostgREST minimal pour projects / generations."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def is_configured(self) -> bool:
        return bool(self._url and self._secret_key)

    @property
    def _url(self) -> str | None:
        raw = self._settings.supabase_url
        return raw.strip() if raw else None

    @property
    def _secret_key(self) -> str | None:
        secret = self._settings.supabase_secret_key
        if secret is None:
            return None
        value = secret.get_secret_value().strip()
        return value or None

    def _headers(self, prefer: str | None = None) -> dict[str, str]:
        key = self._secret_key or ""
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
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

    async def list_projects(self, limit: int = 50) -> list[ProjectRow]:
        if not self.is_configured():
            return []

        async with httpx.AsyncClient(timeout=30.0) as client:
            projects_resp = await client.get(
                f"{self._rest_url()}/projects",
                headers=self._headers(),
                params={
                    "select": "*",
                    "order": "updated_at.desc",
                    "limit": str(limit),
                },
            )
            if projects_resp.status_code >= 400:
                raise SupabaseStoreError(
                    f"Liste projets échouée ({projects_resp.status_code})"
                )
            projects = projects_resp.json()
            if not isinstance(projects, list):
                return []

            result: list[ProjectRow] = []
            for row in projects:
                project_id = str(row["id"])
                count, latest_model = await self._project_generation_stats(
                    client, project_id
                )
                result.append(
                    ProjectRow(
                        id=project_id,
                        title=str(row["title"]),
                        prompt=str(row["prompt"]),
                        project_type=str(row["project_type"]),
                        summary=row.get("summary"),
                        created_at=str(row["created_at"]),
                        updated_at=str(row["updated_at"]),
                        generation_count=count,
                        latest_model=latest_model,
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
                params={"id": f"eq.{project_id}", "select": "*"},
            )
            if project_resp.status_code >= 400:
                raise SupabaseStoreError(
                    f"Lecture projet échouée ({project_resp.status_code})"
                )
            rows = project_resp.json()
            if not rows:
                return None

            row = rows[0]
            count, latest_model = await self._project_generation_stats(
                client, project_id
            )
            project = ProjectRow(
                id=str(row["id"]),
                title=str(row["title"]),
                prompt=str(row["prompt"]),
                project_type=str(row["project_type"]),
                summary=row.get("summary"),
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
                generation_count=count,
                latest_model=latest_model,
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
            if gens_resp.status_code >= 400:
                raise SupabaseStoreError(
                    f"Liste générations échouée ({gens_resp.status_code})"
                )
            generations = [
                _generation_from_row(g)
                for g in gens_resp.json()
                if isinstance(g, dict)
            ]
            return ProjectDetailResponse(project=project, generations=generations)

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
            if find_resp.status_code >= 400:
                raise SupabaseStoreError(
                    f"Recherche projet échouée ({find_resp.status_code})"
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
            if create_resp.status_code >= 400:
                raise SupabaseStoreError(
                    f"Création projet échouée ({create_resp.status_code}): "
                    f"{create_resp.text[:200]}"
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
        files = [{"path": f.path, "content": f.content} for f in gen.files]

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
            "analysis": run_result.analysis.model_dump(),
            "generation_summary": gen.summary,
            "planned_models": run_result.planned_models,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._rest_url()}/generations",
                headers=self._headers("return=representation"),
                json=payload,
            )
            if resp.status_code >= 400:
                raise SupabaseStoreError(
                    f"Insertion génération échouée ({resp.status_code}): "
                    f"{resp.text[:200]}"
                )
            data = resp.json()
            if isinstance(data, list) and data:
                return str(data[0]["id"])
            if isinstance(data, dict) and data.get("id"):
                return str(data["id"])
            raise SupabaseStoreError("Insertion génération sans identifiant.")

    async def _touch_project(self, project_id: str) -> None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.patch(
                f"{self._rest_url()}/projects",
                headers=self._headers(),
                params={"id": f"eq.{project_id}"},
                json={"updated_at": datetime.now(UTC).isoformat()},
            )

    async def _project_generation_stats(
        self, client: httpx.AsyncClient, project_id: str
    ) -> tuple[int, str | None]:
        resp = await client.get(
            f"{self._rest_url()}/generations",
            headers=self._headers(),
            params={
                "project_id": f"eq.{project_id}",
                "select": "model,created_at",
                "order": "created_at.desc",
            },
        )
        if resp.status_code >= 400:
            return 0, None
        rows = resp.json()
        if not isinstance(rows, list):
            return 0, None
        latest = str(rows[0]["model"]) if rows else None
        return len(rows), latest

    def _rest_url(self) -> str:
        return f"{self._url.rstrip('/')}/rest/v1"


def _title_from_prompt(prompt: str, max_len: int = 80) -> str:
    line = prompt.strip().split("\n", 1)[0]
    if len(line) <= max_len:
        return line
    return line[: max_len - 1].rstrip() + "…"


def _generation_from_row(row: dict[str, Any]) -> GenerationRow:
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
        created_at=str(row["created_at"]),
    )


_store: SupabaseStore | None = None


def get_supabase_store() -> SupabaseStore:
    global _store
    if _store is None:
        _store = SupabaseStore()
    return _store

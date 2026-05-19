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
from config import Settings, get_settings, plain_secret_str

logger = logging.getLogger(__name__)


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
        # apikey = anon/publishable ; Authorization = clé secrète (service_role / sb_secret_)
        api_key = self._anon_key or secret
        headers = {
            "apikey": api_key,
            "Authorization": f"Bearer {secret}",
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

        url = f"{self._rest_url()}/projects"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                projects_resp = await client.get(
                    url,
                    headers=self._headers(),
                    params={
                        "select": "*",
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
        hint="Vérifiez SUPABASE_URL, la connexion Internet et que le projet Supabase est actif.",
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
            return "Tables absentes : exécutez supabase/migrations/001_projects_generations.sql"
        return "Route introuvable : vérifiez SUPABASE_URL."
    if status == 403:
        return "Accès refusé (RLS) : le backend doit utiliser la clé service_role."
    if status >= 500:
        return "Erreur serveur Supabase — réessayez plus tard."
    return "Consultez response_body pour le détail PostgREST."


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
        _store = SupabaseStore(get_settings())
    return _store


def reset_supabase_store() -> None:
    """Réinitialise le client après rechargement de la config."""
    global _store
    _store = None

"""
Orchestration Memory Engine — remember, recall, contexte pipeline.
"""

from __future__ import annotations

import logging
from typing import Any

from db.memory_store import MemoryStore, get_memory_store
from knowledge.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class MemoryService:
    """Mémoire persistante avec embeddings optionnels."""

    def __init__(
        self,
        store: MemoryStore | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self._store = store or get_memory_store()
        self._embeddings = embedding_service or EmbeddingService()

    async def remember(
        self,
        title: str,
        content: str,
        memory_type: str,
        category: str = "general",
        importance_score: int = 50,
        project_id: str | None = None,
        agent_id: str | None = None,
    ) -> dict[str, Any]:
        cleaned = (content or "").strip()
        if not cleaned:
            raise ValueError("Contenu mémoire vide.")

        entry = await self._store.create_entry(
            title=title.strip() or "Sans titre",
            content=cleaned,
            memory_type=memory_type,
            category=category,
            importance_score=importance_score,
            project_id=project_id,
            agent_id=agent_id,
        )
        memory_id = str(entry["id"])

        try:
            vector = await self._embeddings.embed_text(cleaned)
            await self._store.create_embedding(
                memory_entry_id=memory_id,
                project_id=project_id,
                embedding=vector,
                embedding_model=self._embeddings.model,
            )
        except (ValueError, Exception) as exc:
            logger.warning(
                "[MemoryEngine] embedding ignoré pour %s — %s", memory_id, exc
            )

        return {"memory_id": memory_id, "title": entry.get("title"), "status": "stored"}

    async def recall(
        self,
        query: str,
        project_id: str | None = None,
        limit: int = 10,
        min_importance: int = 0,
    ) -> list[dict[str, Any]]:
        cleaned = (query or "").strip()
        if not cleaned:
            return []

        try:
            vector = await self._embeddings.embed_text(cleaned)
            hits = await self._store.search_similar(
                vector,
                project_id=project_id,
                limit=limit,
                min_importance=min_importance,
            )
            results = [
                {
                    "memory_id": row.get("memory_id"),
                    "title": row.get("title"),
                    "content": row.get("content"),
                    "memory_type": row.get("memory_type"),
                    "category": row.get("category"),
                    "importance_score": row.get("importance_score"),
                    "similarity": float(row.get("similarity") or 0),
                }
                for row in hits
                if isinstance(row, dict)
            ]
        except ValueError as exc:
            logger.warning("[MemoryEngine] recall sans embedding — %s", exc)
            rows = await self._store.list_entries(
                project_id=project_id,
                min_importance=min_importance,
                limit=limit,
            )
            results = [
                {
                    "memory_id": row.get("id"),
                    "title": row.get("title"),
                    "content": row.get("content"),
                    "memory_type": row.get("memory_type"),
                    "category": row.get("category"),
                    "importance_score": row.get("importance_score"),
                    "similarity": 0.0,
                }
                for row in rows
            ]

        for hit in results:
            mid = str(hit.get("memory_id") or "")
            if mid:
                try:
                    await self._store.increment_access(mid)
                except Exception as exc:
                    logger.warning("[MemoryEngine] increment_access ignoré — %s", exc)

        return results

    async def get_context_for_prompt(
        self,
        query: str,
        project_id: str | None = None,
        max_tokens: int = 2000,
    ) -> str:
        hits = await self.recall(
            query,
            project_id=project_id,
            limit=5,
            min_importance=40,
        )
        if not hits:
            return ""

        lines = ["## Contexte Mémoire", ""]
        used_tokens = 0
        for hit in hits:
            title = str(hit.get("title") or "Mémoire")
            content = str(hit.get("content") or "").strip()
            block = f"### {title}\n{content}\n"
            block_tokens = int(len(block.split()) * 1.3)
            if used_tokens + block_tokens > max_tokens:
                break
            lines.append(block)
            used_tokens += block_tokens

        if len(lines) <= 2:
            return ""
        return "\n".join(lines).strip()

    async def remember_generation(self, brief: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        project_type = str(brief.get("project_type") or "vitrine_next")
        client_name = str(brief.get("client_name") or "Client")
        sector = str(brief.get("sector") or brief.get("secteur") or "—")
        couleur = str(
            brief.get("couleur_primaire")
            or brief.get("primary_color")
            or "—"
        )
        design_system = brief.get("design_system") if isinstance(brief.get("design_system"), dict) else {}
        style_family = str(design_system.get("style_family") or "—")
        duration_ms = int(result.get("duration_ms") or 0)
        url = str(result.get("url") or "")

        title = f"Génération {project_type} — {client_name}"
        content = (
            f"Type : {project_type}\n"
            f"Secteur : {sector}\n"
            f"Client : {client_name}\n"
            f"Couleur primaire : {couleur}\n"
            f"Design family : {style_family}\n"
            f"Durée : {duration_ms}ms\n"
            f"URL démo : {url}\n"
            "Agents utilisés : BriefAI, DesignSystemAI, "
            "GeneratorAI, SupervisorAI, DeployAI"
        )

        return await self.remember(
            title=title,
            content=content,
            memory_type="project",
            category="generation",
            importance_score=80,
            project_id=brief.get("project_id"),
            agent_id="pipeline",
        )

    async def remember_manual(
        self,
        title: str,
        content: str,
        category: str = "preference",
        importance_score: int = 70,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        return await self.remember(
            title=title,
            content=content,
            memory_type="long_term",
            category=category,
            importance_score=importance_score,
            project_id=project_id,
        )


_service: MemoryService | None = None


def get_memory_service() -> MemoryService:
    global _service
    if _service is None:
        _service = MemoryService()
    return _service


def reset_memory_service() -> None:
    global _service
    _service = None

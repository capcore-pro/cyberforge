"""
Orchestration Knowledge Engine — ingestion, recherche et contexte RAG.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

from db.knowledge_store import KnowledgeStore, get_knowledge_store
from knowledge.chunking_service import ChunkingService
from knowledge.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

SUPPORTED_UPLOAD_SUFFIXES = {".txt", ".md"}
SIMILARITY_THRESHOLD = 0.5


class KnowledgeService:
    """Pipeline ingestion + recherche sémantique."""

    def __init__(
        self,
        store: KnowledgeStore | None = None,
        embedding_service: EmbeddingService | None = None,
        chunking_service: ChunkingService | None = None,
    ) -> None:
        self._store = store or get_knowledge_store()
        self._embeddings = embedding_service or EmbeddingService()
        self._chunking = chunking_service or ChunkingService()

    async def ingest_text(
        self,
        title: str,
        content: str,
        project_id: str | None = None,
        source_type: str = "manual",
        language: str = "fr",
    ) -> dict[str, Any]:
        cleaned = (content or "").strip()
        if not cleaned:
            raise ValueError("Contenu vide.")

        content_hash = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()
        document = await self._store.create_document(
            title=title.strip() or "Sans titre",
            content=cleaned,
            source_type=source_type,
            project_id=project_id,
            language=language,
            content_hash=content_hash,
        )
        document_id = str(document["id"])

        chunks = self._chunking.chunk_document(cleaned, title=title)
        if not chunks:
            chunks = [
                {
                    "index": 0,
                    "content": cleaned,
                    "token_count": self._chunking._estimate_tokens(cleaned),
                }
            ]

        texts = [str(c["content"]) for c in chunks]
        vectors = await self._embeddings.embed_texts(texts)

        for chunk, vector in zip(chunks, vectors, strict=True):
            saved_chunk = await self._store.create_chunk(
                document_id=document_id,
                chunk_index=int(chunk["index"]),
                content=str(chunk["content"]),
                token_count=int(chunk.get("token_count") or 0),
            )
            await self._store.create_embedding(
                chunk_id=str(saved_chunk["id"]),
                document_id=document_id,
                project_id=project_id,
                embedding=vector,
                embedding_model=self._embeddings.model,
            )

        return {
            "document_id": document_id,
            "chunks_count": len(chunks),
            "status": "indexed",
        }

    async def ingest_file(
        self,
        file_path: str,
        title: str,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        path = Path(file_path)
        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_UPLOAD_SUFFIXES:
            raise ValueError("Formats supportés : .txt, .md")
        content = path.read_text(encoding="utf-8")
        return await self.ingest_text(
            title=title or path.stem,
            content=content,
            project_id=project_id,
            source_type="uploaded",
        )

    async def search(
        self,
        query: str,
        project_id: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        cleaned = (query or "").strip()
        if not cleaned:
            return []

        vector = await self._embeddings.embed_text(cleaned)
        hits = await self._store.search_similar(
            vector,
            project_id=project_id,
            limit=limit,
        )
        return [
            {
                "chunk_id": row.get("chunk_id"),
                "document_id": row.get("document_id"),
                "document_title": row.get("document_title"),
                "content": row.get("content"),
                "similarity": float(row.get("similarity") or 0),
            }
            for row in hits
            if isinstance(row, dict)
        ]

    async def get_context_for_prompt(
        self,
        query: str,
        project_id: str | None = None,
        max_tokens: int = 4000,
    ) -> str:
        hits = await self.search(query, project_id=project_id, limit=10)
        # Seuil abaissé — documents courts ou requêtes sémantiquement éloignées
        # À remonter à 0.7 quand la base knowledge sera plus dense
        relevant = [h for h in hits if float(h.get("similarity") or 0) >= SIMILARITY_THRESHOLD]
        if not relevant:
            return ""

        lines = ["## Contexte Knowledge Engine", ""]
        used_tokens = 0
        for hit in relevant:
            title = str(hit.get("document_title") or "Document")
            content = str(hit.get("content") or "").strip()
            similarity = float(hit.get("similarity") or 0)
            block = f"### {title} (similarité {similarity:.2f})\n{content}\n"
            block_tokens = int(len(block.split()) * 1.3)
            if used_tokens + block_tokens > max_tokens:
                break
            lines.append(block)
            used_tokens += block_tokens

        if len(lines) <= 2:
            return ""
        return "\n".join(lines).strip()


_service: KnowledgeService | None = None


def get_knowledge_service() -> KnowledgeService:
    global _service
    if _service is None:
        _service = KnowledgeService()
    return _service


def reset_knowledge_service() -> None:
    global _service
    _service = None

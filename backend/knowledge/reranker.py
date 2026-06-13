"""Reranking léger des chunks RAG avant injection dans le prompt."""

from __future__ import annotations

from typing import Any


class SimpleReranker:
    def rerank(
        self,
        query: str,
        chunks: list[dict],
        top_k: int = 5,
    ) -> list[dict]:
        query_terms = set(query.lower().split())
        scored: list[dict[str, Any]] = []
        for chunk in chunks:
            content = chunk.get("content", "")
            base_score = chunk.get(
                "combined_score",
                chunk.get("similarity", 0),
            )
            content_lower = content.lower()
            term_matches = sum(
                1 for t in query_terms
                if t in content_lower
            )
            term_boost = term_matches * 0.05
            position_boost = 0.02 if chunk.get(
                "chunk_index", 1
            ) == 0 else 0
            length_penalty = (
                -0.1 if len(content) < 100 else 0
            )
            final_score = (
                base_score + term_boost
                + position_boost + length_penalty
            )
            scored.append({
                **chunk,
                "rerank_score": final_score,
            })
        return sorted(
            scored,
            key=lambda x: x["rerank_score"],
            reverse=True,
        )[:top_k]


reranker = SimpleReranker()

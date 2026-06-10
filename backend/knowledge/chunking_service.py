"""
Découpage de documents pour le Knowledge Engine.
"""

from __future__ import annotations

import re
from typing import Any

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_OVERLAP = 200
TOKEN_FACTOR = 1.3


class ChunkingService:
    """Découpe le texte en chunks avec overlap token-based."""

    def __init__(
        self,
        *,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        overlap: int = DEFAULT_OVERLAP,
    ) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        return max(1, int(len(text.split()) * TOKEN_FACTOR))

    @staticmethod
    def _clean_content(text: str) -> str:
        cleaned = (text or "").replace("\r\n", "\n").replace("\r", "\n")
        cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", cleaned)
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    def chunk_text(self, text: str) -> list[dict[str, Any]]:
        """Découpe le texte en chunks avec overlap."""
        words = (text or "").split()
        if not words:
            return []

        chunks: list[dict[str, Any]] = []
        start = 0
        index = 0
        chunk_word_size = max(1, int(self.chunk_size / TOKEN_FACTOR))
        overlap_words = max(0, int(self.overlap / TOKEN_FACTOR))

        while start < len(words):
            end = min(len(words), start + chunk_word_size)
            content = " ".join(words[start:end]).strip()
            if content:
                chunks.append(
                    {
                        "index": index,
                        "content": content,
                        "token_count": self._estimate_tokens(content),
                    }
                )
                index += 1
            if end >= len(words):
                break
            start = max(0, end - overlap_words)

        return chunks

    def chunk_document(self, content: str, title: str = "") -> list[dict[str, Any]]:
        """Nettoie puis découpe un document."""
        _ = title  # réservé métadonnées futures
        cleaned = self._clean_content(content)
        return self.chunk_text(cleaned)

"""
Service d'embeddings OpenAI pour le Knowledge Engine.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from config import Settings, get_settings
from security.llm_secrets import get_effective_llm_key

logger = logging.getLogger(__name__)

OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"
DEFAULT_MODEL = "text-embedding-3-small"
DEFAULT_DIMENSIONS = 1536
MAX_BATCH_SIZE = 100


class EmbeddingService:
    """Génère des vecteurs via l'API OpenAI embeddings."""

    def __init__(
        self,
        *,
        provider: str = "openai",
        model: str = DEFAULT_MODEL,
        dimensions: int = DEFAULT_DIMENSIONS,
        settings: Settings | None = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.dimensions = dimensions
        self._settings = settings or get_settings()

    def _api_key(self) -> str:
        key = get_effective_llm_key("OPENAI_API_KEY", self._settings)
        if not key:
            raise ValueError(
                "OPENAI_API_KEY absente — configurez-la dans Paramètres → Secrets."
            )
        return key

    async def embed_text(self, text: str) -> list[float]:
        """Embed un texte unique."""
        vectors = await self.embed_texts([text])
        return vectors[0]

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed une liste de textes (batch max 100)."""
        if not texts:
            return []
        if len(texts) > MAX_BATCH_SIZE:
            raise ValueError(f"Maximum {MAX_BATCH_SIZE} textes par batch.")

        api_key = self._api_key()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "input": texts if len(texts) > 1 else texts[0],
            "model": self.model,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    OPENAI_EMBEDDINGS_URL,
                    headers=headers,
                    json=payload,
                )
                if response.status_code >= 400:
                    logger.error(
                        "[EmbeddingService] OpenAI HTTP %s — %s",
                        response.status_code,
                        response.text[:500],
                    )
                    response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            logger.error("[EmbeddingService] erreur API OpenAI — %s", exc)
            raise

        items = data.get("data") or []
        if not isinstance(items, list) or not items:
            raise ValueError("Réponse OpenAI embeddings vide.")

        ordered = sorted(items, key=lambda x: int(x.get("index", 0)))
        vectors: list[list[float]] = []
        for item in ordered:
            embedding = item.get("embedding")
            if not isinstance(embedding, list):
                raise ValueError("Embedding invalide dans la réponse OpenAI.")
            vectors.append([float(v) for v in embedding])
        return vectors

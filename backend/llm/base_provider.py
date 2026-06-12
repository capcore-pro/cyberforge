"""Contrat commun des fournisseurs LLM."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMRequest:
    messages: list[dict]
    system_prompt: str | None = None
    model: str | None = None
    max_tokens: int = 8096
    temperature: float = 0.7


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class BaseLLMProvider(ABC):
    provider_slug: str
    default_model: str

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...

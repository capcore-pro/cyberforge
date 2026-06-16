"""Client Mistral AI — briefs et tâches répétitives (volume économique)."""

from __future__ import annotations

import logging
import sys
from typing import Any

# Force le bon chemin Python 3.11 (évite conflit mistralai / mauvais site-packages)
mistralai_path = r"C:\Users\mathi\AppData\Local\Programs\Python\Python311\Lib\site-packages"
if mistralai_path not in sys.path:
    sys.path.insert(0, mistralai_path)

try:
    from mistralai import Mistral
except ImportError:
    # mistralai >= 2.x : package namespace, client dans mistralai.client
    from mistralai.client import Mistral

from config import get_settings, plain_secret_str

logger = logging.getLogger(__name__)


class MistralClient:
  def __init__(self) -> None:
    settings = get_settings()
    api_key = plain_secret_str(settings.mistral_api_key)
    self._api_key = api_key
    self.client: Any = None
    if api_key:
      self.client = Mistral(api_key=api_key)
    self.small_model = "mistral-small-latest"
    self.large_model = "mistral-large-latest"

  def is_configured(self) -> bool:
    return bool(self.client and self._api_key)

  async def complete(
    self,
    messages: list[dict],
    model: str = "mistral-small-latest",
    max_tokens: int = 4096,
    temperature: float = 0.7,
    system_prompt: str | None = None,
  ) -> tuple[str, dict[str, int]]:
    if not self.client:
      raise RuntimeError("Mistral non configuré")

    payload = list(messages)
    if system_prompt:
      payload = [{"role": "system", "content": system_prompt}, *payload]

    response = await self.client.chat.complete_async(
      model=model,
      messages=payload,
      max_tokens=max_tokens,
      temperature=temperature,
    )
    content = ""
    choice = response.choices[0] if response.choices else None
    if choice and choice.message:
      content = str(choice.message.content or "")
    usage = getattr(response, "usage", None)
    inp = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
    out = int(getattr(usage, "completion_tokens", 0) or 0) if usage else 0
    return content, {"input_tokens": inp, "output_tokens": out, "total_tokens": inp + out}

  async def complete_small(
    self,
    messages: list[dict],
    max_tokens: int = 2048,
    *,
    system_prompt: str | None = None,
    temperature: float = 0.7,
  ) -> tuple[str, dict[str, int]]:
    return await self.complete(
      messages,
      self.small_model,
      max_tokens,
      temperature,
      system_prompt=system_prompt,
    )

  async def complete_large(
    self,
    messages: list[dict],
    max_tokens: int = 4096,
    *,
    system_prompt: str | None = None,
    temperature: float = 0.7,
  ) -> tuple[str, dict[str, int]]:
    return await self.complete(
      messages,
      self.large_model,
      max_tokens,
      temperature,
      system_prompt=system_prompt,
    )


mistral_client = MistralClient()

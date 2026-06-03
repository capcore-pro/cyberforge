"""Tests route generate-prompt — corps Anthropic et gestion d'erreurs."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException

from api.routes.generator_prompt import (
    MAX_OUTPUT_TOKENS,
    PROMPT_MODEL,
    GeneratePromptRequest,
    _anthropic_request_body,
    _call_anthropic_messages,
    generate_cyberforge_prompt,
)


def test_anthropic_request_body_format() -> None:
    body = _anthropic_request_body(
        system="sys",
        user_message="hello",
        model=PROMPT_MODEL,
    )
    assert body == {
        "model": PROMPT_MODEL,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "system": "sys",
        "messages": [{"role": "user", "content": "hello"}],
    }
    assert body["max_tokens"] == 1024


@pytest.mark.asyncio
async def test_call_anthropic_uses_utf8_json_body() -> None:
    client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock()
    mock_response.status_code = 200
    client.post.return_value = mock_response

    await _call_anthropic_messages(
        client=client,
        api_key="sk-test",
        model=PROMPT_MODEL,
        system="system prompt",
        user_message="user idea",
    )

    client.post.assert_awaited_once()
    call_kwargs = client.post.await_args.kwargs
    assert call_kwargs["headers"]["x-api-key"] == "sk-test"
    assert call_kwargs["headers"]["anthropic-version"] == "2023-06-01"
    assert "Content-Type" in call_kwargs["headers"]
    payload = json.loads(call_kwargs["content"].decode("utf-8"))
    assert payload["model"] == PROMPT_MODEL
    assert payload["messages"][0]["content"] == "user idea"


@pytest.mark.asyncio
async def test_generate_prompt_raises_on_anthropic_400() -> None:
    error_body = {
        "type": "error",
        "error": {
            "type": "invalid_request_error",
            "message": "model: claude-sonnet-4-5",
        },
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = json.dumps(error_body)
    mock_resp.headers = {"request-id": "req_test123"}
    mock_resp.json.return_value = error_body

    with (
        patch(
            "api.routes.generator_prompt.get_effective_llm_key_for_http",
            return_value="sk-ant-test",
        ),
        patch(
            "api.routes.generator_prompt._log_api_key_resolution",
            return_value="vault",
        ),
        patch(
            "api.routes.generator_prompt._call_anthropic_messages",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await generate_cyberforge_prompt(
            GeneratePromptRequest(project_kind="vitrine", idea="Salon de coiffure moderne")
        )

    assert exc_info.value.status_code == 502
    assert "model" in exc_info.value.detail.lower()

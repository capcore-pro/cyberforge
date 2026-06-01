"""Tests des pings de clés API (httpx mocké)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from tools.api_key_tester import test_api_key


def _mock_response(status_code: int) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    return resp


@patch("tools.api_key_tester.httpx.Client")
def test_anthropic_uses_models_endpoint(mock_client_cls: MagicMock) -> None:
    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_client
    mock_client.request.return_value = _mock_response(200)

    valid, msg = test_api_key("anthropic", "sk-ant-test")

    assert valid is True
    assert msg == "Connexion réussie"
    call = mock_client.request.call_args
    assert call.args[0] == "GET"
    assert call.args[1] == "https://api.anthropic.com/v1/models"
    headers = call.kwargs["headers"]
    assert headers["x-api-key"] == "sk-ant-test"
    assert headers["anthropic-version"] == "2023-06-01"


@patch("tools.api_key_tester.httpx.Client")
def test_deepseek_uses_models_endpoint(mock_client_cls: MagicMock) -> None:
    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_client
    mock_client.request.return_value = _mock_response(200)

    valid, _ = test_api_key("deepseek", "ds-key")

    assert valid is True
    call = mock_client.request.call_args
    assert call.args[1] == "https://api.deepseek.com/models"
    assert call.kwargs["headers"]["Authorization"] == "Bearer ds-key"


@patch("tools.api_key_tester.httpx.Client")
def test_v0_projects_endpoint_valid(mock_client_cls: MagicMock) -> None:
    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_client
    mock_client.get.return_value = _mock_response(200)

    valid, msg = test_api_key("v0", "v0_test_key")

    assert valid is True
    assert msg == "Connexion réussie"
    mock_client.get.assert_called_once_with(
        "https://api.v0.dev/v1/projects",
        headers={"Authorization": "Bearer v0_test_key"},
    )


@patch("tools.api_key_tester.httpx.Client")
def test_v0_accepts_key_when_no_public_test(mock_client_cls: MagicMock) -> None:
    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_client
    mock_client.get.return_value = _mock_response(404)

    valid, msg = test_api_key("v0", "v0_test_key")

    assert valid is True
    assert "pas de test API public" in msg


def test_v0_accepts_key_on_network_error() -> None:
    with patch("tools.api_key_tester.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client
        mock_client.get.side_effect = httpx.ConnectError("offline")

        valid, msg = test_api_key("v0", "v0_test_key")

    assert valid is True
    assert "indisponible" in msg

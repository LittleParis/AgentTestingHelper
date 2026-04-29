"""Tests for LLMClient text-proxy isolation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.utils.llm_client import LLMClient


def _mock_settings():
    return MagicMock(
        llm_api_key="test_key_123456",
        llm_model="astron-code-latest",
        llm_base_url="https://maas-coding-api.cn-huabei-1.xf-yun.com/v2",
        llm_temperature=0.1,
        llm_max_tokens=256,
        llm_retry_attempts=1,
        llm_retry_delay=0.1,
        llm_use_env_proxy=False,
        llm_proxy_url=None,
    )


@patch("core.utils.llm_client.ChatOpenAI")
@patch("core.utils.llm_client.httpx.Client")
@patch("core.models.get_settings")
def test_llm_client_defaults_to_direct_connection(
    mock_get_settings,
    mock_httpx_client,
    mock_chat_openai,
    monkeypatch,
):
    mock_get_settings.return_value = _mock_settings()
    mock_httpx_client.return_value = MagicMock()
    mock_chat_openai.return_value = MagicMock()
    monkeypatch.delenv("LLM_USE_ENV_PROXY", raising=False)
    monkeypatch.delenv("LLM_PROXY_URL", raising=False)

    LLMClient()

    assert any(
        call.kwargs.get("trust_env") is False
        for call in mock_httpx_client.call_args_list
    )


@patch("core.utils.llm_client.ChatOpenAI")
@patch("core.utils.llm_client.httpx.Client")
@patch("core.models.get_settings")
def test_llm_client_supports_dedicated_proxy_url(
    mock_get_settings,
    mock_httpx_client,
    mock_chat_openai,
    monkeypatch,
):
    mock_get_settings.return_value = _mock_settings()
    mock_httpx_client.return_value = MagicMock()
    mock_chat_openai.return_value = MagicMock()
    monkeypatch.setenv("LLM_PROXY_URL", "http://127.0.0.1:8888")

    LLMClient()

    assert any(
        call.kwargs.get("proxy") == "http://127.0.0.1:8888"
        for call in mock_httpx_client.call_args_list
    )

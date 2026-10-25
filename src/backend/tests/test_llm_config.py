"""LLM provider switch: OpenAI or Grok."""

import os
from pathlib import Path

import pytest

from recruitment.llm_config import (
    XAI_BASE_URL,
    LlmConfigError,
    build_llm,
    resolve_llm,
)


def test_default_provider_is_openai() -> None:
    settings = resolve_llm({"OPENAI_API_KEY": "sk-test", "OPENAI_MODEL": "gpt-4o-mini"})
    assert settings.provider == "openai"
    assert settings.model == "gpt-4o-mini"
    assert settings.api_key_env == "OPENAI_API_KEY"
    assert settings.base_url is None


def test_grok_uses_xai_key_and_base_url() -> None:
    settings = resolve_llm(
        {"LLM_PROVIDER": "Grok", "GROK_API_KEY": "xai-alias", "GROK_MODEL": "grok-4.6"}
    )
    assert settings.provider == "grok"
    assert settings.model == "grok-4.6"
    assert settings.api_key == "xai-alias"
    assert settings.base_url == XAI_BASE_URL
    assert settings.api_key_env == "XAI_API_KEY"


def test_xai_key_wins_over_grok_alias() -> None:
    settings = resolve_llm(
        {"LLM_PROVIDER": "grok", "XAI_API_KEY": "primary", "GROK_API_KEY": "alias"}
    )
    assert settings.api_key == "primary"
    assert settings.model == "grok-4.7"


def test_unknown_provider() -> None:
    with pytest.raises(LlmConfigError):
        resolve_llm({"LLM_PROVIDER": "openrouter"})


def test_grok_client_targets_xai(tmp_path: Path) -> None:
    os.environ["XDG_DATA_HOME"] = str(tmp_path)
    settings = resolve_llm({"LLM_PROVIDER": "grok", "XAI_API_KEY": "test-xai"})
    llm = build_llm(settings, temperature=0.2, max_tokens=8192)
    assert llm.model == "grok-4.7"
    assert llm.base_url == XAI_BASE_URL
    assert llm.api_key == "test-xai"

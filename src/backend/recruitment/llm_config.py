"""Select one LLM provider for a process: OpenAI, Grok (xAI), or OpenRouter."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

OPENAI_PROVIDER = "openai"
GROK_PROVIDER = "grok"
OPENROUTER_PROVIDER = "openrouter"
PROVIDERS = (OPENAI_PROVIDER, GROK_PROVIDER, OPENROUTER_PROVIDER)

DEFAULT_OPENAI_MODEL = "gpt-4o"
DEFAULT_GROK_MODEL = "grok-4.7"
DEFAULT_OPENROUTER_MODEL = "openai/gpt-4o"
XAI_BASE_URL = "https://api.x.ai/v1"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class LlmConfigError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class LlmSettings:
    provider: str
    model: str
    api_key: str
    api_key_env: str
    base_url: str | None = None


def resolve_llm(environ: Mapping[str, str]) -> LlmSettings:
    provider = (environ.get("LLM_PROVIDER") or OPENAI_PROVIDER).strip().lower()
    if provider not in PROVIDERS:
        raise LlmConfigError("LLM_PROVIDER must be openai, grok, or openrouter.")
    if provider == GROK_PROVIDER:
        api_key = (environ.get("XAI_API_KEY") or environ.get("GROK_API_KEY") or "").strip()
        model = (environ.get("GROK_MODEL") or DEFAULT_GROK_MODEL).strip() or DEFAULT_GROK_MODEL
        return LlmSettings(
            provider=GROK_PROVIDER,
            model=model,
            api_key=api_key,
            api_key_env="XAI_API_KEY",
            base_url=XAI_BASE_URL,
        )
    if provider == OPENROUTER_PROVIDER:
        api_key = (environ.get("OPENROUTER_API_KEY") or "").strip()
        raw_model = (environ.get("OPENROUTER_MODEL") or DEFAULT_OPENROUTER_MODEL).strip()
        model = _openrouter_model_id(raw_model)
        return LlmSettings(
            provider=OPENROUTER_PROVIDER,
            model=model,
            api_key=api_key,
            api_key_env="OPENROUTER_API_KEY",
            base_url=OPENROUTER_BASE_URL,
        )
    api_key = (environ.get("OPENAI_API_KEY") or "").strip()
    model = (environ.get("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL).strip() or DEFAULT_OPENAI_MODEL
    return LlmSettings(
        provider=OPENAI_PROVIDER,
        model=model,
        api_key=api_key,
        api_key_env="OPENAI_API_KEY",
        base_url=None,
    )


def _openrouter_model_id(raw: str) -> str:
    """OpenRouter model id without CrewAI's routing prefix.

    CrewAI selects its OpenRouter client when the model starts with
    ``openrouter/``. The id sent to the API is the remainder
    (``openai/gpt-4o``). An env value that already has that prefix is stored
    without it.
    """
    model = raw.strip() or DEFAULT_OPENROUTER_MODEL
    if model.lower().startswith("openrouter/"):
        model = model.split("/", 1)[1].strip()
    return model or DEFAULT_OPENROUTER_MODEL


def missing_llm_key(settings: LlmSettings) -> str | None:
    if settings.api_key:
        return None
    return settings.api_key_env


def build_llm(settings: LlmSettings, *, temperature: float, max_tokens: int) -> Any:
    from crewai import LLM

    kwargs: dict[str, Any] = {
        "model": settings.model,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if settings.api_key:
        kwargs["api_key"] = settings.api_key
    if settings.provider == OPENROUTER_PROVIDER:
        kwargs["model"] = f"openrouter/{settings.model}"
        kwargs["base_url"] = settings.base_url
    elif settings.base_url:
        kwargs["base_url"] = settings.base_url
        kwargs["custom_openai"] = True
    return LLM(**kwargs)

"""Redacted logs. Secret values are never written.

Stdout follows ``LOG_LEVEL`` (default INFO). The same lines that pass that
threshold are appended to ``logs/trace.log``.
Request and response bodies are not logged.
"""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Mapping
from datetime import datetime, timezone

from recruitment.paths import BUILD_LOG_DIR, TRACE_LOG_PATH

SECRET_ENV_NAMES = ("OPENAI_API_KEY", "XAI_API_KEY", "GROK_API_KEY", "SERPER_API_KEY")

logger = logging.getLogger("recruitment")
_CONFIGURED = False


def redact(text: str, environ: Mapping[str, str] | None = None) -> str:
    source = os.environ if environ is None else environ
    cleaned = text
    for name in SECRET_ENV_NAMES:
        value = source.get(name) or ""
        if value and value in cleaned:
            cleaned = cleaned.replace(value, "[REDACTED]")
    return cleaned


def configure_logging(environ: Mapping[str, str] | None = None) -> None:
    """Attach one stdout handler and apply LOG_LEVEL. Safe to call again."""
    global _CONFIGURED
    source = os.environ if environ is None else environ
    logger.setLevel(_level_from(source))
    logger.propagate = True
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    formatter.converter = time_gmtime
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    _CONFIGURED = True


def time_gmtime(timestamp: float):
    return datetime.fromtimestamp(timestamp, timezone.utc).timetuple()


def log_event(
    message: str,
    environ: Mapping[str, str] | None = None,
    *,
    level: int = logging.INFO,
) -> None:
    safe = redact(message, environ)
    if not logger.isEnabledFor(level):
        return
    logger.log(level, safe)
    try:
        BUILD_LOG_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        level_name = logging.getLevelName(level)
        with TRACE_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(f"{stamp} {level_name} {safe}\n")
    except OSError as exc:
        logger.warning("trace log was not written: %s", exc)


def startup_message(
    *,
    version: str,
    env: str,
    provider: str,
    crew_load_ok: bool,
    tracing: bool,
) -> str:
    load = "ok" if crew_load_ok else "failed"
    flag = "true" if tracing else "false"
    return (
        f"startup version={version} env={env} llm_provider={provider} "
        f"crew_load={load} crewai_tracing={flag}"
    )


def _level_from(source: Mapping[str, str]) -> int:
    name = (source.get("LOG_LEVEL") or "INFO").strip().upper()
    value = logging.getLevelName(name)
    if isinstance(value, int):
        return value
    return logging.INFO

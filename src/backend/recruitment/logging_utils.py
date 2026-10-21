"""Redacted logs. Secret values are never written."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from recruitment.paths import BUILD_LOG_DIR, TRACE_LOG_PATH

SECRET_ENV_NAMES = ("OPENAI_API_KEY", "SERPER_API_KEY")

logger = logging.getLogger("recruitment")


def redact(text: str, environ: dict[str, str] | None = None) -> str:
    source = os.environ if environ is None else environ
    cleaned = text
    for name in SECRET_ENV_NAMES:
        value = source.get(name) or ""
        if value and value in cleaned:
            cleaned = cleaned.replace(value, "[REDACTED]")
    return cleaned


def log_event(message: str, environ: dict[str, str] | None = None) -> None:
    safe = redact(message, environ)
    logger.info(safe)
    try:
        BUILD_LOG_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with TRACE_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(f"{stamp} {safe}\n")
    except OSError as exc:
        logger.warning("trace log was not written: %s", exc)

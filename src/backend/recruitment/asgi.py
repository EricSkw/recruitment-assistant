"""Uvicorn application. Loads the repo .env without overriding existing variables."""

import logging
import os

from dotenv import load_dotenv

from recruitment import __version__
from recruitment.api import create_app
from recruitment.crew_runtime import crew_tracing_enabled
from recruitment.logging_utils import log_event, redact, startup_message
from recruitment.paths import REPO_ROOT

load_dotenv(REPO_ROOT / ".env")
app = create_app()
log_event(
    startup_message(
        version=__version__,
        env=os.environ.get("APP_ENV", "development"),
        provider=os.environ.get("LLM_PROVIDER", "openai"),
        crew_load_ok=not app.state.load_error,
        tracing=crew_tracing_enabled(),
    )
)
if app.state.load_error:
    detail = redact(str(app.state.load_error))[:300]
    log_event(f"startup_crew_load_failed detail={detail}", level=logging.ERROR)

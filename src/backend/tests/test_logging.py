"""Startup, access, and tracing logs. Bodies and secret values stay out."""

import logging

import pytest
from fastapi.testclient import TestClient

from recruitment.api import create_app
from recruitment.crew_runtime import crew_tracing_enabled
from recruitment.logging_utils import redact, startup_message
from recruitment.results import KickoffResult

from tests.test_api import KEYS, VALID, _client


def test_startup_message_names_runtime_flags() -> None:
    text = startup_message(
        version="0.1.0",
        env="development",
        provider="openai",
        crew_load_ok=True,
        tracing=False,
    )
    assert "startup version=0.1.0" in text
    assert "llm_provider=openai" in text
    assert "crew_load=ok" in text
    assert "crewai_tracing=false" in text


def test_redact_replaces_secret_values() -> None:
    cleaned = redact("key=super-secret", {"OPENAI_API_KEY": "super-secret"})
    assert "super-secret" not in cleaned
    assert "[REDACTED]" in cleaned


def test_tracing_is_on_unless_disabled(monkeypatch) -> None:
    monkeypatch.delenv("CREWAI_TRACING_ENABLED", raising=False)
    assert crew_tracing_enabled() is True
    monkeypatch.setenv("CREWAI_TRACING_ENABLED", "true")
    assert crew_tracing_enabled() is True
    monkeypatch.setenv("CREWAI_TRACING_ENABLED", "false")
    assert crew_tracing_enabled() is False


def test_access_log_records_status_not_body(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="recruitment")
    client = _client(lambda inputs, on_task: KickoffResult("unused"))
    marker = "UniqueDescZZZ-do-not-log"
    response = client.post(
        "/api/runs",
        json={"job_requirements": {**VALID, "title": " ", "description": marker}},
    )
    assert response.status_code == 422
    text = caplog.text
    assert "api method=POST path=/api/runs status=422" in text
    assert marker not in text
    assert "your_openai" not in text


def test_health_access_is_debug(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger="recruitment")
    client = _client(lambda inputs, on_task: KickoffResult("unused"))
    logging.getLogger("recruitment").setLevel(logging.DEBUG)
    response = client.get("/health")
    assert response.status_code == 200
    assert "api method=GET path=/health status=200" in caplog.text


def test_unhandled_exception_logs_type_only(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.ERROR, logger="recruitment")
    app = create_app(
        runner=lambda inputs, on_task: KickoffResult("unused"),
        environ=KEYS,
        load_crew=False,
    )
    client = TestClient(app, raise_server_exceptions=True)

    def _boom(*_args, **_kwargs):
        raise RuntimeError("boom-secret-value")

    app.state.service.start = _boom
    with pytest.raises(RuntimeError):
        client.post("/api/runs", json={"job_requirements": VALID})
    assert "api_exception method=POST path=/api/runs error=RuntimeError" in caplog.text
    assert "boom-secret-value" not in caplog.text

"""FastAPI surface for health checks and crew runs."""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from typing import Any

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from recruitment.gate import (
    PayloadError,
    confirmation_requested,
    evaluate_gate,
    merge_requirements,
    normalize_requirements,
    parse_raw_blob,
)
from recruitment.logging_utils import redact
from recruitment.models import RunRequest, error_payload
from recruitment.results import KickoffResult
from recruitment.runs import WALL_CLOCK_SECONDS, RunService

REQUIRED_KEYS = ("OPENAI_API_KEY", "SERPER_API_KEY")
Runner = Callable[[dict[str, str], Callable[[str], None]], KickoffResult]


def missing_api_keys(environ: Mapping[str, str]) -> list[str]:
    return [name for name in REQUIRED_KEYS if not (environ.get(name) or "").strip()]


def resolve_candidate_limit(requested: int | None, environ: Mapping[str, str]) -> int:
    if requested is not None:
        return requested
    raw = (environ.get("CANDIDATE_LIMIT") or "10").strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise PayloadError("CANDIDATE_LIMIT must be an integer from 5 to 10.") from exc
    if value < 5 or value > 10:
        raise PayloadError("CANDIDATE_LIMIT must be an integer from 5 to 10.")
    return value


def _default_runner(model: str) -> Runner:
    from recruitment.crew_runtime import kickoff

    def _run(inputs: dict[str, str], on_task: Callable[[str], None]) -> KickoffResult:
        return kickoff(inputs, on_task=on_task, model=model)

    return _run


def _load_error(model: str) -> str | None:
    try:
        from recruitment.crew_runtime import build_crew

        build_crew(model=model)
    except Exception as exc:
        return redact(str(exc)) or "The crew failed to load."
    return None


def create_app(
    *,
    runner: Runner | None = None,
    environ: Mapping[str, str] | None = None,
    wall_clock_s: int = WALL_CLOCK_SECONDS,
    load_crew: bool = True,
) -> FastAPI:
    source = os.environ if environ is None else environ
    env_map = {key: str(value) for key, value in source.items()}
    model = (env_map.get("OPENAI_MODEL") or "gpt-4o").strip() or "gpt-4o"
    load_error = None
    if runner is None and load_crew:
        load_error = _load_error(model)
    if runner is None:
        runner = _default_runner(model)
    service = RunService(runner, wall_clock_s=wall_clock_s, environ=env_map)
    app = FastAPI(title="Recruitment Assistant", version="0.1.0")
    app.state.service = service
    app.state.load_error = load_error
    app.state.environ = env_map

    @app.exception_handler(RequestValidationError)
    async def _validation(_request: Any, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        loc = ".".join(str(part) for part in first.get("loc", ()))
        detail = first.get("msg", "Request validation failed.")
        message = f"{loc}: {detail}" if loc else str(detail)
        return JSONResponse(status_code=422, content=error_payload("VALIDATION", message))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/runs")
    def create_run(body: RunRequest) -> JSONResponse:
        if app.state.load_error:
            return JSONResponse(
                status_code=503,
                content=error_payload(
                    "CREW_FAILURE",
                    "The crew failed to load. Check agent and task YAML.",
                ),
            )
        missing = missing_api_keys(app.state.environ)
        if missing:
            names = ", ".join(missing)
            return JSONResponse(
                status_code=503,
                content=error_payload(
                    "MISSING_API_KEY",
                    f"Missing required environment variable: {names}.",
                ),
            )
        try:
            prepared = _prepare(body, app.state.environ)
        except PayloadError as exc:
            return JSONResponse(
                status_code=422,
                content=error_payload("VALIDATION", exc.message),
            )
        gate = prepared["gate"]
        if gate.status == "blocked":
            return JSONResponse(
                status_code=422,
                content=error_payload("VALIDATION", _gap_message(gate.gaps)),
            )
        if gate.status == "needs_clarification":
            return JSONResponse(
                status_code=200,
                content={
                    "run_id": None,
                    "status": "needs_clarification",
                    "gaps": [
                        {
                            "field": gap.field,
                            "reason": gap.reason,
                            "run_anyway_allowed": gap.run_anyway_allowed,
                        }
                        for gap in gate.gaps
                    ],
                },
            )
        run_id = service.start(prepared["inputs"], gate.assumptions)
        if run_id is None:
            return JSONResponse(
                status_code=409,
                content=error_payload(
                    "CREW_BUSY",
                    "A crew is already active. Wait until it finishes.",
                ),
            )
        return JSONResponse(
            status_code=202,
            content={"run_id": run_id, "status": "queued", "gaps": []},
        )

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str) -> JSONResponse:
        record = service.get(run_id)
        if record is None:
            return JSONResponse(
                status_code=404,
                content=error_payload("VALIDATION", "Unknown run id.", run_id),
            )
        return JSONResponse(status_code=200, content=record.to_dict())

    return app


def _gap_message(gaps: list[Any]) -> str:
    pieces = [f"{gap.field}: {gap.reason}" for gap in gaps]
    return "Job requirements are incomplete. " + " ".join(pieces)


def _prepare(body: RunRequest, environ: Mapping[str, str]) -> dict[str, Any]:
    blob_text = body.raw_blob
    confirm = confirmation_requested(body.confirm_run_anyway, blob_text)
    blob = parse_raw_blob(None if confirm and _is_phrase(blob_text) else blob_text)
    explicit = None
    if body.job_requirements is not None:
        explicit = body.job_requirements.model_dump(exclude_unset=True)
    job = normalize_requirements(merge_requirements(blob, explicit))
    limit = resolve_candidate_limit(body.candidate_limit, environ)
    gate = evaluate_gate(job, confirm_run_anyway=confirm)
    assumption_text = "\n".join(gate.assumptions) if gate.assumptions else "None"
    inputs = {
        "job_requirements": json.dumps(job, ensure_ascii=False, indent=2),
        "assumptions": assumption_text,
        "candidate_limit": str(limit),
    }
    return {"gate": gate, "inputs": inputs}


def _is_phrase(raw_blob: str | None) -> bool:
    return bool(raw_blob and raw_blob.strip().casefold() == "run anyway")

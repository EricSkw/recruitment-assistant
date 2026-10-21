"""HTTP schemas for POST /api/runs and GET /api/runs/{run_id}."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Remote = Literal["onsite", "hybrid", "remote"]


class JobRequirementsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    description: str | None = None
    responsibilities: str | None = None
    requirements: str | None = None
    preferred_qualifications: str | None = None
    location: str | None = None
    remote: Remote | None = None
    perks_and_benefits: str | None = None


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_requirements: JobRequirementsIn | None = None
    raw_blob: str | None = None
    confirm_run_anyway: bool = False
    candidate_limit: int | None = Field(default=None, ge=5, le=10)


class ErrorBody(BaseModel):
    code: str
    message: str
    run_id: str | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorBody


def error_payload(code: str, message: str, run_id: str | None = None) -> dict[str, Any]:
    return ErrorEnvelope(
        error=ErrorBody(code=code, message=message, run_id=run_id)
    ).model_dump()

"""Deterministic clarify-before-kickoff gate (SAD §2). No LLM."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

import yaml

PAYLOAD_MAX_CHARS = 12_000
TITLE_MAX_CHARS = 200
FIELD_MAX_CHARS = 4_000
MIN_MUST_HAVE_TOKENS = 3

TEXT_FIELDS = (
    "title",
    "description",
    "responsibilities",
    "requirements",
    "preferred_qualifications",
    "location",
    "perks_and_benefits",
)

REMOTE_VALUES = {"onsite", "hybrid", "remote"}

VAGUE_PHRASES = (
    "good culture fit",
    "culture fit",
    "team player",
    "rockstar",
    "ninja",
    "fast learner",
    "self-starter",
    "self starter",
    "passionate",
    "passion",
    "go-getter",
    "go getter",
    "wear many hats",
    "hit the ground running",
    "work hard play hard",
)

STOPWORDS = frozenset(
    {"a", "an", "the", "and", "or", "of", "to", "for", "with", "in", "on", "be"}
)

SENIORITY_TERMS = (
    "intern",
    "junior",
    "jr",
    "mid-level",
    "mid level",
    "senior",
    "sr",
    "staff",
    "principal",
    "lead",
    "manager",
    "director",
    "vp",
    "executive",
    "entry-level",
    "entry level",
)

SENIORITY_YEARS = re.compile(r"\b\d+\+?\s*years?\b", re.IGNORECASE)

LOCATION_TERMS = (
    "remote",
    "hybrid",
    "onsite",
    "on-site",
    "work from home",
    "wfh",
)

ASSUMPTION_SENIORITY = (
    "seniority unspecified; matcher must mark seniority fit as not assessed"
)
ASSUMPTION_LOCATION = (
    "location unspecified; search the public web without a geography penalty"
)

_TOKEN = re.compile(r"[A-Za-z0-9]+")


class PayloadError(Exception):
    """Schema or size failure. Maps to HTTP 422 VALIDATION."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass
class Gap:
    field: str
    reason: str
    run_anyway_allowed: bool


@dataclass
class GateResult:
    status: str
    gaps: list[Gap] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    job_requirements: dict[str, Any] = field(default_factory=dict)


def parse_raw_blob(raw_blob: str | None) -> dict[str, Any]:
    if raw_blob is None or not str(raw_blob).strip():
        return {}
    text = str(raw_blob)
    if len(text) > PAYLOAD_MAX_CHARS:
        raise PayloadError("Serialized payload exceeds 12000 characters.")
    if text.strip().casefold() == "run anyway":
        return {}
    try:
        loaded = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise PayloadError("raw_blob is not valid YAML.") from exc
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise PayloadError("raw_blob must be a YAML mapping of job fields.")
    return {str(key): value for key, value in loaded.items()}


def merge_requirements(
    blob: dict[str, Any],
    explicit: dict[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(blob)
    if explicit:
        merged.update(explicit)
    return merged


def normalize_requirements(raw: dict[str, Any]) -> dict[str, Any]:
    unknown = set(raw) - set(TEXT_FIELDS) - {"remote"}
    if unknown:
        names = ", ".join(sorted(unknown))
        raise PayloadError(f"Unknown job field: {names}.")

    normalized: dict[str, Any] = {}
    for key in TEXT_FIELDS:
        value = raw.get(key)
        if value is None:
            normalized[key] = ""
            continue
        if not isinstance(value, str):
            raise PayloadError(f"{key} must be a string.")
        text = value.strip()
        limit = TITLE_MAX_CHARS if key == "title" else FIELD_MAX_CHARS
        if len(text) > limit:
            raise PayloadError(f"{key} exceeds {limit} characters.")
        normalized[key] = text

    remote = raw.get("remote")
    if remote is None or remote == "":
        normalized["remote"] = None
    elif not isinstance(remote, str) or remote not in REMOTE_VALUES:
        raise PayloadError("remote must be onsite, hybrid, remote, or null.")
    else:
        normalized["remote"] = remote

    serialized = json.dumps(normalized, ensure_ascii=False, sort_keys=True)
    if len(serialized) > PAYLOAD_MAX_CHARS:
        raise PayloadError("Serialized payload exceeds 12000 characters.")
    return normalized


def strip_vague_phrases(requirements: str) -> str:
    text = requirements
    for phrase in sorted(VAGUE_PHRASES, key=len, reverse=True):
        text = re.sub(re.escape(phrase), " ", text, flags=re.IGNORECASE)
    return text


def must_haves_empty(requirements: str) -> bool:
    stripped = strip_vague_phrases(requirements or "")
    tokens = [
        token
        for token in _TOKEN.findall(stripped)
        if token.casefold() not in STOPWORDS
    ]
    return len(tokens) < MIN_MUST_HAVE_TOKENS


def _combined(job: dict[str, Any]) -> str:
    parts = (
        job.get("title", ""),
        job.get("description", ""),
        job.get("responsibilities", ""),
        job.get("requirements", ""),
    )
    return "\n".join(part for part in parts if part)


def _contains_term(text: str, term: str) -> bool:
    pattern = r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def seniority_present(job: dict[str, Any]) -> bool:
    text = _combined(job)
    if SENIORITY_YEARS.search(text):
        return True
    return any(_contains_term(text, term) for term in SENIORITY_TERMS)


def location_present(job: dict[str, Any]) -> bool:
    if (job.get("location") or "").strip():
        return True
    if job.get("remote"):
        return True
    text = _combined(job)
    return any(_contains_term(text, term) for term in LOCATION_TERMS)


def evaluate_gate(job: dict[str, Any], *, confirm_run_anyway: bool) -> GateResult:
    gaps: list[Gap] = []
    title = (job.get("title") or "").strip()
    if len(title) < 2:
        gaps.append(
            Gap(
                field="title",
                reason="Title is required and must be at least 2 characters.",
                run_anyway_allowed=False,
            )
        )
    if must_haves_empty(job.get("requirements") or ""):
        gaps.append(
            Gap(
                field="requirements",
                reason=(
                    "Must-have skills are empty after removing vague phrases. "
                    "Add observable requirements."
                ),
                run_anyway_allowed=False,
            )
        )

    hard = [gap for gap in gaps if not gap.run_anyway_allowed]
    clarify: list[Gap] = []
    if not hard:
        if not seniority_present(job):
            clarify.append(
                Gap(
                    field="seniority",
                    reason=(
                        "Seniority is missing. Add a level or years of "
                        "experience, or confirm run anyway."
                    ),
                    run_anyway_allowed=True,
                )
            )
        if not location_present(job):
            clarify.append(
                Gap(
                    field="location",
                    reason=(
                        "Location or remote constraint is missing. Add it, "
                        "or confirm run anyway."
                    ),
                    run_anyway_allowed=True,
                )
            )

    if hard:
        return GateResult(status="blocked", gaps=hard + clarify, job_requirements=job)

    assumptions: list[str] = []
    if clarify and not confirm_run_anyway:
        return GateResult(
            status="needs_clarification",
            gaps=clarify,
            job_requirements=job,
        )
    if clarify and confirm_run_anyway:
        if any(gap.field == "seniority" for gap in clarify):
            assumptions.append(ASSUMPTION_SENIORITY)
        if any(gap.field == "location" for gap in clarify):
            assumptions.append(ASSUMPTION_LOCATION)
    return GateResult(
        status="ok",
        assumptions=assumptions,
        job_requirements=job,
    )


def confirmation_requested(confirm_run_anyway: bool, raw_blob: str | None) -> bool:
    if confirm_run_anyway:
        return True
    if raw_blob is None:
        return False
    return raw_blob.strip().casefold() == "run anyway"

"""One-shot command line for the recruitment crew.

Uses the same gate, provider switch, and kickoff as ``POST /api/runs``.
The report is printed on stdout after the run. Status, task names, and
errors go to stderr. Lifecycle logs still use the process logger.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import uuid
from collections.abc import Callable, Mapping
from typing import Any

from recruitment.api import missing_api_keys, resolve_candidate_limit
from recruitment.crew_runtime import kickoff
from recruitment.gate import PayloadError, evaluate_gate, normalize_requirements
from recruitment.llm_config import LlmConfigError, LlmSettings, resolve_llm
from recruitment.logging_utils import configure_logging, redact
from recruitment.paths import REPO_ROOT, RUNS_DIR
from recruitment.results import KickoffFailed, KickoffResult
from recruitment.runs import WALL_CLOCK_SECONDS

Runner = Callable[[dict[str, str], Callable[[str], None]], KickoffResult]

EXIT_OK = 0
EXIT_CREW = 1
EXIT_VALIDATION = 2
EXIT_CONFIG = 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.cli",
        description=(
            "Run one recruitment crew from the command line. "
            "The clarify-before-kickoff gate runs before any model call."
        ),
    )
    parser.add_argument(
        "--job-description",
        required=True,
        help="Job title. The same text is stored as the description.",
    )
    parser.add_argument(
        "--requirements",
        required=True,
        help="Must-have skills and experience.",
    )
    parser.add_argument(
        "--location",
        default="",
        help="City or region. Optional when --remote or --run-anyway is set.",
    )
    parser.add_argument(
        "--remote",
        choices=("onsite", "hybrid", "remote"),
        default=None,
        help="Work mode. Optional.",
    )
    parser.add_argument(
        "--run-anyway",
        action="store_true",
        help="Continue when only seniority or location is missing.",
    )
    parser.add_argument(
        "--candidate-limit",
        type=int,
        default=None,
        help="Candidates to request, from 5 to 10. Default is CANDIDATE_LIMIT or 10.",
    )
    return parser


def main(
    argv: list[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    runner: Runner | None = None,
    export_report: bool = True,
    wall_clock_s: int = WALL_CLOCK_SECONDS,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    source = _environment(environ)
    configure_logging(source)
    try:
        settings = resolve_llm(source)
        missing = missing_api_keys(source)
    except LlmConfigError as exc:
        return _error(exc.message, EXIT_CONFIG)
    if missing:
        names = ", ".join(missing)
        return _error(f"Missing required environment variable: {names}.", EXIT_CONFIG)
    try:
        job = _job_from_args(args)
        limit = resolve_candidate_limit(args.candidate_limit, source)
        gate = evaluate_gate(normalize_requirements(job), confirm_run_anyway=args.run_anyway)
    except PayloadError as exc:
        return _error(exc.message, EXIT_VALIDATION)
    if gate.status == "blocked":
        return _error(_gap_message(gate.gaps), EXIT_VALIDATION)
    if gate.status == "needs_clarification":
        return _error(
            _gap_message(gate.gaps) + " Re-run with --run-anyway, or add --location or --remote.",
            EXIT_VALIDATION,
        )
    assumption_text = "\n".join(gate.assumptions) if gate.assumptions else "None"
    inputs = {
        "job_requirements": json.dumps(gate.job_requirements, ensure_ascii=False, indent=2),
        "assumptions": assumption_text,
        "candidate_limit": str(limit),
    }
    if gate.assumptions:
        print("Assumptions:", file=sys.stderr)
        for line in gate.assumptions:
            print(f"- {line}", file=sys.stderr)
    active = runner or _live_runner(settings)
    try:
        result = _run_with_budget(active, inputs, wall_clock_s)
    except KickoffFailed as exc:
        if exc.partial:
            print(redact(exc.partial, source))
            return _error(f"{exc.code}: {exc.message}", EXIT_CREW)
        return _error(f"{exc.code}: {exc.message}", EXIT_CREW)
    except Exception as exc:
        return _error(f"CREW_FAILURE: {redact(str(exc), source) or type(exc).__name__}", EXIT_CREW)
    report = redact(result.report_markdown, source)
    if export_report:
        _export(report)
    print(report)
    return EXIT_OK


def _environment(environ: Mapping[str, str] | None) -> Mapping[str, str]:
    if environ is not None:
        return environ
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
    return os.environ


def _job_from_args(args: argparse.Namespace) -> dict[str, Any]:
    job: dict[str, Any] = {
        "title": args.job_description,
        "description": args.job_description,
        "requirements": args.requirements,
    }
    if args.location:
        job["location"] = args.location
    if args.remote:
        job["remote"] = args.remote
    return job


def _gap_message(gaps: list[Any]) -> str:
    pieces = [f"{gap.field}: {gap.reason}" for gap in gaps]
    return "Job requirements are incomplete. " + " ".join(pieces)


def _live_runner(settings: LlmSettings) -> Runner:
    def _run(inputs: dict[str, str], on_task: Callable[[str], None]) -> KickoffResult:
        return kickoff(inputs, on_task=on_task, llm_settings=settings)

    return _run


def _run_with_budget(runner: Runner, inputs: dict[str, str], wall_clock_s: int) -> KickoffResult:
    box: dict[str, Any] = {}

    def _on_task(name: str) -> None:
        print(f"task: {name}", file=sys.stderr)

    def _work() -> None:
        try:
            box["result"] = runner(inputs, _on_task)
        except Exception as exc:
            box["error"] = exc

    thread = threading.Thread(target=_work, name="recruitment-cli", daemon=True)
    thread.start()
    thread.join(wall_clock_s)
    if thread.is_alive():
        raise KickoffFailed(
            "TIMEOUT",
            f"Kickoff exceeded the {wall_clock_s} second limit.",
        )
    if "error" in box:
        error = box["error"]
        if isinstance(error, KickoffFailed):
            raise error
        raise KickoffFailed(
            "CREW_FAILURE",
            redact(str(error)) or "The recruitment crew failed.",
        ) from error
    return box["result"]


def _export(report: str) -> None:
    run_id = str(uuid.uuid4())
    try:
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        path = RUNS_DIR / f"{run_id}.md"
        path.write_text(report, encoding="utf-8")
    except OSError as exc:
        print(f"report file was not written: {exc}", file=sys.stderr)
        return
    print(f"report file: {path}", file=sys.stderr)


def _error(message: str, code: int) -> int:
    print(message, file=sys.stderr)
    return code

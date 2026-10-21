"""In-memory run records and the single-crew supervisor."""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from recruitment.logging_utils import log_event, redact
from recruitment.paths import RUNS_DIR
from recruitment.results import KickoffFailed, KickoffResult

Runner = Callable[[dict[str, str], Callable[[str], None]], KickoffResult]
TERMINAL = {"completed", "failed", "partial"}
WALL_CLOCK_SECONDS = 480


@dataclass
class RunRecord:
    run_id: str
    status: str
    current_task: str | None = None
    partial: bool = False
    assumptions: list[str] = field(default_factory=list)
    report_markdown: str | None = None
    error: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "current_task": self.current_task,
            "partial": self.partial,
            "assumptions": list(self.assumptions),
            "report_markdown": self.report_markdown,
            "error": self.error,
        }


class RunService:
    def __init__(
        self,
        runner: Runner,
        wall_clock_s: int = WALL_CLOCK_SECONDS,
        environ: dict[str, str] | None = None,
    ) -> None:
        self.runner = runner
        self.wall_clock_s = wall_clock_s
        self.environ = environ
        self._lock = threading.Lock()
        self._runs: dict[str, RunRecord] = {}

    def busy(self) -> bool:
        with self._lock:
            return any(record.status in {"queued", "running"} for record in self._runs.values())

    def get(self, run_id: str) -> RunRecord | None:
        with self._lock:
            return self._runs.get(run_id)

    def start(self, inputs: dict[str, str], assumptions: list[str]) -> str | None:
        run_id = str(uuid.uuid4())
        record = RunRecord(run_id=run_id, status="queued", assumptions=list(assumptions))
        with self._lock:
            if any(item.status in {"queued", "running"} for item in self._runs.values()):
                return None
            self._runs[run_id] = record
        log_event(f"run_queued run_id={run_id}", self.environ)
        thread = threading.Thread(
            target=self._execute,
            args=(run_id, inputs),
            name=f"recruitment-{run_id}",
            daemon=True,
        )
        thread.start()
        return run_id

    def _execute(self, run_id: str, inputs: dict[str, str]) -> None:
        self._update(run_id, status="running", current_task="research_candidates")
        log_event(f"run_start run_id={run_id} task=research_candidates", self.environ)
        done = threading.Event()
        box: dict[str, Any] = {}

        def _on_task(name: str) -> None:
            self._update(run_id, status="running", current_task=name)
            log_event(f"run_task run_id={run_id} task={name}", self.environ)

        def _work() -> None:
            try:
                box["result"] = self.runner(inputs, _on_task)
            except KickoffFailed as exc:
                box["failed"] = exc
            except Exception as exc:
                box["failed"] = KickoffFailed(
                    "CREW_FAILURE",
                    redact(str(exc), self.environ) or "The recruitment crew failed.",
                )
            finally:
                done.set()

        threading.Thread(target=_work, name=f"kickoff-{run_id}", daemon=True).start()
        if not done.wait(self.wall_clock_s):
            self._fail(
                run_id,
                "TIMEOUT",
                (
                    f"Kickoff exceeded the {self.wall_clock_s} second limit. "
                    f"Last task: {self._task_name(run_id)}."
                ),
                partial_text=None,
            )
            log_event(f"run_timeout run_id={run_id}", self.environ)
            return
        if "failed" in box:
            failed: KickoffFailed = box["failed"]
            self._fail(run_id, failed.code, failed.message, failed.partial)
            return
        result: KickoffResult = box["result"]
        self._complete(run_id, result)

    def _task_name(self, run_id: str) -> str:
        record = self.get(run_id)
        if record and record.current_task:
            return record.current_task
        return "unknown"

    def _update(self, run_id: str, **changes: Any) -> None:
        with self._lock:
            record = self._runs[run_id]
            if record.status in TERMINAL:
                return
            for key, value in changes.items():
                setattr(record, key, value)

    def _fail(
        self,
        run_id: str,
        code: str,
        message: str,
        partial_text: str | None,
    ) -> None:
        with self._lock:
            record = self._runs[run_id]
            if record.status in TERMINAL:
                return
            record.error = {"code": code, "message": message, "run_id": run_id}
            if partial_text:
                record.status = "partial"
                record.partial = True
                record.report_markdown = partial_text
            else:
                record.status = "failed"
                record.partial = False
        log_event(f"run_end run_id={run_id} code={code}", self.environ)

    def _complete(self, run_id: str, result: KickoffResult) -> None:
        with self._lock:
            record = self._runs[run_id]
            if record.status in TERMINAL:
                return
            record.status = "completed"
            record.partial = False
            record.current_task = None
            record.report_markdown = result.report_markdown
            record.error = None
        self._export(run_id, result.report_markdown)
        log_event(
            (
                f"run_complete run_id={run_id} tokens={result.total_tokens} "
                f"search_calls={result.search_calls}"
            ),
            self.environ,
        )

    def _export(self, run_id: str, markdown: str) -> None:
        try:
            RUNS_DIR.mkdir(parents=True, exist_ok=True)
            path = RUNS_DIR / f"{run_id}.md"
            path.write_text(redact(markdown, self.environ), encoding="utf-8")
        except OSError as exc:
            log_event(f"run_export_failed run_id={run_id} error={exc}", self.environ)

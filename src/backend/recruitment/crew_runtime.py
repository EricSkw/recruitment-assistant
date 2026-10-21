"""Load YAML agents and tasks and run one sequential kickoff."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from recruitment.config_check import (
    AGENT_ORDER,
    MAX_EXECUTION_TIME,
    MAX_ITER,
    MAX_RETRY,
    MAX_RPM,
    MAX_TOKENS,
    TASK_CONTEXT,
    TASK_ORDER,
    TEMPERATURE,
    TOOL_IDS,
    agent_for,
    load_validated,
    write_prompt_trace,
)
from recruitment.guardrail import report_guardrail
from recruitment.logging_utils import log_event
from recruitment.results import KickoffFailed, KickoffResult

OnTask = Callable[[str], None]


def build_crew(on_task: OnTask | None = None, model: str | None = None) -> Any:
    from crewai import Agent, Crew, LLM, Process, Task

    from recruitment.tools import build_tool

    agents_cfg, tasks_cfg = load_validated()
    write_prompt_trace(agents_cfg, tasks_cfg)
    resolved_model = model or os.environ.get("OPENAI_MODEL", "gpt-4o") or "gpt-4o"

    llm = LLM(model=resolved_model, temperature=TEMPERATURE, max_tokens=MAX_TOKENS)
    agents: dict[str, Any] = {}
    for agent_id in AGENT_ORDER:
        spec = agents_cfg[agent_id]
        agents[agent_id] = Agent(
            role=str(spec["role"]).strip(),
            goal=str(spec["goal"]).strip(),
            backstory=str(spec["backstory"]).strip(),
            tools=[build_tool(tool_id) for tool_id in TOOL_IDS[agent_id]],
            llm=llm,
            allow_delegation=False,
            max_iter=MAX_ITER,
            max_retry_limit=MAX_RETRY,
            max_execution_time=MAX_EXECUTION_TIME,
            verbose=False,
        )

    built: dict[str, Any] = {}
    for task_id in TASK_ORDER:
        spec = tasks_cfg[task_id]
        context = [built[name] for name in TASK_CONTEXT[task_id]]
        built[task_id] = Task(
            name=task_id,
            description=str(spec["description"]).strip(),
            expected_output=str(spec["expected_output"]).strip(),
            agent=agents[agent_for(task_id)],
            context=context or None,
            callback=_task_callback(task_id, on_task),
            guardrail=report_guardrail if task_id == "compile_report" else None,
            guardrail_max_retries=MAX_RETRY,
        )

    return Crew(
        name="recruitment",
        agents=[agents[agent_id] for agent_id in AGENT_ORDER],
        tasks=[built[task_id] for task_id in TASK_ORDER],
        process=Process.sequential,
        memory=False,
        max_rpm=MAX_RPM,
        verbose=False,
        cache=False,
    )


def _task_callback(task_id: str, on_task: OnTask | None) -> Callable[..., None]:
    def _callback(_output: Any) -> None:
        log_event(f"task_stop task={task_id}")
        index = TASK_ORDER.index(task_id)
        if on_task and index + 1 < len(TASK_ORDER):
            nxt = TASK_ORDER[index + 1]
            log_event(f"task_start task={nxt}")
            on_task(nxt)

    return _callback


def _partial_markdown(crew: Any) -> str | None:
    parts: list[str] = []
    for task in crew.tasks:
        output = getattr(task, "output", None)
        raw = getattr(output, "raw", None)
        if raw:
            parts.append(f"### Partial {task.name}\n\n{raw}")
    if not parts:
        return None
    return "\n\n".join(parts)


def _failure_code(exc: BaseException) -> str:
    text = str(exc).casefold()
    if "guardrail" in text:
        return "GUARDRAIL"
    return "CREW_FAILURE"


def kickoff(
    inputs: dict[str, str],
    on_task: OnTask | None = None,
    model: str | None = None,
) -> KickoffResult:
    from recruitment.tools import current_search_calls, reset_search_calls

    required = ("job_requirements", "assumptions", "candidate_limit")
    missing = [key for key in required if key not in inputs]
    if missing:
        raise KickoffFailed("CREW_FAILURE", "Crew inputs are missing required keys.")
    reset_search_calls()
    if on_task:
        log_event("task_start task=research_candidates")
        on_task("research_candidates")
    crew = build_crew(on_task=on_task, model=model)
    try:
        result = crew.kickoff(inputs=inputs)
    except Exception as exc:
        log_event(f"kickoff_error code={_failure_code(exc)}")
        raise KickoffFailed(
            _failure_code(exc),
            "The recruitment crew failed. Partial output is labeled partial.",
            partial=_partial_markdown(crew),
        ) from exc
    usage = getattr(result, "token_usage", None)
    total_tokens = int(getattr(usage, "total_tokens", 0) or 0)
    log_event(
        f"kickoff_complete tokens={total_tokens} search_calls={current_search_calls()}"
    )
    return KickoffResult(
        report_markdown=str(getattr(result, "raw", "") or ""),
        total_tokens=total_tokens,
        search_calls=current_search_calls(),
    )

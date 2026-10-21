"""YAML contracts for the recruitment crew. No CrewAI import."""

from __future__ import annotations

from typing import Any

import yaml

from recruitment.guardrail import REQUIRED_HEADINGS
from recruitment.paths import AGENTS_YAML, PROMPT_TRACE_PATH, TASKS_YAML

AGENT_ORDER = ("researcher", "matcher", "communicator", "reporter")
TASK_ORDER = (
    "research_candidates",
    "match_and_score",
    "draft_outreach",
    "compile_report",
)
TASK_CONTEXT = {
    "research_candidates": (),
    "match_and_score": ("research_candidates",),
    "draft_outreach": ("research_candidates", "match_and_score"),
    "compile_report": (
        "research_candidates",
        "match_and_score",
        "draft_outreach",
    ),
}
TOOL_IDS = {
    "researcher": ("serper_search", "public_scrape"),
    "matcher": ("serper_search", "public_scrape"),
    "communicator": ("serper_search", "public_scrape"),
    "reporter": (),
}
FORBIDDEN_SNIPPETS = ("LINKEDIN_COOKIE", "LI_AT", "Selenium", "send_mail")
MAX_ITER = 12
MAX_RETRY = 2
MAX_EXECUTION_TIME = 150
MAX_RPM = 20
TEMPERATURE = 0.2
MAX_TOKENS = 8192


def load_yaml(path: Any) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet.casefold() in text.casefold():
            raise RuntimeError(f"Forbidden tool configuration: {snippet}")
    loaded = yaml.safe_load(text)
    if not isinstance(loaded, dict):
        raise RuntimeError(f"{path.name} must be a mapping.")
    return loaded


def agent_for(task_id: str) -> str:
    return {
        "research_candidates": "researcher",
        "match_and_score": "matcher",
        "draft_outreach": "communicator",
        "compile_report": "reporter",
    }[task_id]


def validate_configs(agents: dict[str, Any], tasks: dict[str, Any]) -> None:
    if tuple(agents) != AGENT_ORDER:
        raise RuntimeError(
            "agents.yaml must define researcher, matcher, communicator, reporter."
        )
    if tuple(tasks) != TASK_ORDER:
        raise RuntimeError("tasks.yaml task order does not match the sequential crew.")
    for agent_id, spec in agents.items():
        if spec.get("allow_delegation") not in (False, "false"):
            raise RuntimeError(f"{agent_id} must set allow_delegation false.")
        if int(spec.get("max_iter", 0)) > MAX_ITER:
            raise RuntimeError(f"{agent_id} max_iter exceeds {MAX_ITER}.")
        if int(spec.get("max_retry_limit", 0)) < MAX_RETRY:
            raise RuntimeError(
                f"{agent_id} max_retry_limit must be at least {MAX_RETRY}."
            )
        tools = tuple(spec.get("tools") or ())
        if tools != TOOL_IDS[agent_id]:
            raise RuntimeError(f"{agent_id} tools do not match the allowed set.")
    for task_id, spec in tasks.items():
        context = tuple(spec.get("context") or ())
        if context != TASK_CONTEXT[task_id]:
            raise RuntimeError(f"{task_id} context does not match the SAD task graph.")
        if spec.get("agent") != agent_for(task_id):
            raise RuntimeError(f"{task_id} is bound to the wrong agent.")
    expected = tasks["compile_report"]["expected_output"]
    for heading in REQUIRED_HEADINGS:
        if heading not in expected:
            raise RuntimeError(f"compile_report expected_output is missing {heading}.")
    if "without wrapping code fences" not in expected:
        raise RuntimeError("compile_report expected_output must forbid code fences.")


def load_validated() -> tuple[dict[str, Any], dict[str, Any]]:
    agents = load_yaml(AGENTS_YAML)
    tasks = load_yaml(TASKS_YAML)
    validate_configs(agents, tasks)
    return agents, tasks


def write_prompt_trace(agents: dict[str, Any], tasks: dict[str, Any]) -> None:
    """Record YAML prompts. Kickoff inputs are omitted because they may be a requisition."""
    lines = [
        "# Prompt trace — recruitment crew",
        "",
        "Templates below are the agent and task prompts before kickoff interpolation.",
        "Secret environment values are not part of this trace.",
        "",
    ]
    for agent_id, spec in agents.items():
        lines.append(f"## Agent `{agent_id}`")
        lines.append(f"- role: {str(spec.get('role', '')).strip()}")
        lines.append(f"- goal: {str(spec.get('goal', '')).strip()}")
        lines.append(f"- backstory: {str(spec.get('backstory', '')).strip()}")
        lines.append("")
    for task_id, spec in tasks.items():
        lines.append(f"## Task `{task_id}`")
        lines.append(str(spec.get("description", "")).strip())
        lines.append("")
        lines.append("Expected output:")
        lines.append(str(spec.get("expected_output", "")).strip())
        lines.append("")
    PROMPT_TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROMPT_TRACE_PATH.write_text("\n".join(lines), encoding="utf-8")

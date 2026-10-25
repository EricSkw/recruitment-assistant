"""Repository paths used by the backend."""

from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parents[1]
AGENTS_YAML = BACKEND_DIR / "config" / "agents.yaml"
TASKS_YAML = BACKEND_DIR / "config" / "tasks.yaml"
RUNS_DIR = REPO_ROOT / "var" / "runs"
BUILD_LOG_DIR = REPO_ROOT / "logs"
PROMPT_TRACE_PATH = BUILD_LOG_DIR / "prompt-trace.md"
TRACE_LOG_PATH = BUILD_LOG_DIR / "trace.log"

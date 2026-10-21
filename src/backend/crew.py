"""CrewAI entrypoint. Agents and tasks are loaded from config/*.yaml."""

from recruitment.crew_runtime import build_crew, kickoff

__all__ = ["build_crew", "kickoff"]

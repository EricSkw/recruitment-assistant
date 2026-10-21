"""Kickoff result types. Kept free of the CrewAI import."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class KickoffResult:
    report_markdown: str
    total_tokens: int = 0
    search_calls: int = 0


class KickoffFailed(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        partial: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.partial = partial

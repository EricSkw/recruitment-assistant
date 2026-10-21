"""CrewAI tool bindings. Search is counted; scrape refuses blocked hosts."""

from __future__ import annotations

from typing import Any

from crewai_tools import ScrapeWebsiteTool, SerperDevTool

from recruitment.scrape_policy import scrape_refusal_reason

_search_calls = 0


def reset_search_calls() -> None:
    global _search_calls
    _search_calls = 0


def current_search_calls() -> int:
    return _search_calls


class CountingSerperTool(SerperDevTool):
    """Serper search that increments a process-local call counter."""

    def _run(self, **kwargs: Any) -> Any:
        global _search_calls
        _search_calls += 1
        return super()._run(**kwargs)


class PublicScrapeTool(ScrapeWebsiteTool):
    """Scrape public pages. No cookies, no Authorization, no linkedin.com."""

    name: str = "public_website_scrape"
    description: str = (
        "Read a public http or https page. Refuses linkedin.com and "
        "non-public URLs. Does not send cookies or Authorization headers."
    )

    def _run(self, **kwargs: Any) -> Any:
        website_url = kwargs.get("website_url", self.website_url)
        reason = scrape_refusal_reason(str(website_url or ""))
        if reason:
            return reason
        self.cookies = None
        headers = dict(self.headers or {})
        headers.pop("Authorization", None)
        headers.pop("Cookie", None)
        self.headers = headers
        return super()._run(**kwargs)


def build_tool(tool_id: str) -> Any:
    if tool_id == "serper_search":
        return CountingSerperTool()
    if tool_id == "public_scrape":
        return PublicScrapeTool()
    raise RuntimeError(f"Unknown tool id: {tool_id}")

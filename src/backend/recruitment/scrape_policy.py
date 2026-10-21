"""Public-page scrape policy. LinkedIn hosts and non-HTTP URLs are refused."""

from __future__ import annotations

from urllib.parse import urlparse

DENIED_HOSTS = frozenset({"linkedin.com", "www.linkedin.com"})


def scrape_refusal_reason(url: str) -> str | None:
    """Return an operator-safe refusal, or None when the URL may be fetched."""
    parsed = urlparse((url or "").strip())
    if parsed.scheme not in {"http", "https"}:
        return "Only public http and https pages can be scraped."
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        return "The scrape URL has no host."
    if host in DENIED_HOSTS or host.endswith(".linkedin.com"):
        return "Scraping linkedin.com is not allowed. Cite the search URL instead."
    return None

"""Stubs for capabilities the PRD defers. They are not called by the MVP API."""


def persist_last_n_reports(limit: int) -> None:
    """P1. MVP keeps the in-memory run map and one optional var/runs file."""
    raise NotImplementedError("P1 local report history is deferred.")


def stream_task_tokens() -> None:
    """P1. MVP returns the report on poll, not a token stream."""
    raise NotImplementedError("P1 token streaming is deferred.")


def export_pdf() -> None:
    """P1. MVP download is the markdown report."""
    raise NotImplementedError("P1 PDF export is deferred.")


def send_outreach() -> None:
    """Forbidden in MVP. The communicator drafts text and does not send it."""
    raise NotImplementedError("Sending outreach is forbidden.")


def export_to_ats() -> None:
    """P2. No Greenhouse, Ashby, or other ATS connector."""
    raise NotImplementedError("ATS export is deferred.")


def authenticate_operator() -> None:
    """P2. MVP trusts the loopback bind and has no login."""
    raise NotImplementedError("Multi-user auth is deferred.")

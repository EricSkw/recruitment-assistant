"""Report heading guardrail for compile_report (SAD §2)."""

from typing import Any

REQUIRED_HEADINGS = (
    "## Job requirements",
    "## Assumptions",
    "## Candidate profiles",
    "## Ranked scores and justifications",
    "## Outreach drafts",
    "## Sources",
    "## Recommendations for recruiter review",
)

NOT_SENT_PHRASE = "not sent"


def report_text(output: Any) -> str:
    raw = getattr(output, "raw", None)
    if isinstance(raw, str):
        return raw
    return str(output)


def report_guardrail(output: Any) -> tuple[bool, Any]:
    text = report_text(output)
    stripped = text.lstrip()
    if stripped.startswith("```"):
        return (False, "Report must not start with a code fence.")
    missing = [heading for heading in REQUIRED_HEADINGS if heading not in text]
    if missing:
        joined = ", ".join(missing)
        return (False, f"Report is missing required headings: {joined}.")
    if NOT_SENT_PHRASE not in text.casefold():
        return (False, "Report must state that outreach drafts were not sent.")
    return (True, output)

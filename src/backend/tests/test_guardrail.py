"""Report guardrail and rubric weights."""

from types import SimpleNamespace

from recruitment.guardrail import REQUIRED_HEADINGS, report_guardrail
from recruitment.rubric import RUBRIC_POINTS, rubric_total


def _report(body: str) -> SimpleNamespace:
    return SimpleNamespace(raw=body)


def _valid_body() -> str:
    parts = [f"{heading}\n\nContent." for heading in REQUIRED_HEADINGS]
    parts.append("Outreach drafts were not sent.")
    return "\n".join(parts)


def test_rubric_sums_to_100() -> None:
    assert rubric_total() == 100
    assert RUBRIC_POINTS["skills_match"] == 40
    assert RUBRIC_POINTS["seniority_fit"] == 20
    assert RUBRIC_POINTS["evidence_quality"] == 25
    assert RUBRIC_POINTS["location_remote_fit"] == 15


def test_guardrail_accepts_fixture_report() -> None:
    ok, output = report_guardrail(_report(_valid_body()))
    assert ok is True
    assert output.raw.startswith("## Job requirements")


def test_guardrail_rejects_code_fence() -> None:
    ok, message = report_guardrail(_report("```\n" + _valid_body()))
    assert ok is False
    assert "code fence" in message


def test_guardrail_rejects_missing_heading_and_send_phrase() -> None:
    ok, message = report_guardrail(_report("## Job requirements\n\nOnly one heading."))
    assert ok is False
    assert "missing required headings" in message

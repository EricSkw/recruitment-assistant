"""AC-011 gate: empty title, empty must-haves, vague phrases, run anyway."""

import pytest

from recruitment.gate import (
    ASSUMPTION_LOCATION,
    ASSUMPTION_SENIORITY,
    evaluate_gate,
    must_haves_empty,
    normalize_requirements,
    parse_raw_blob,
    merge_requirements,
    PayloadError,
)


def _job(**overrides: str | None) -> dict:
    base = {
        "title": "Rails Engineer",
        "description": "Build the product.",
        "responsibilities": "Ship features.",
        "requirements": "Ruby on Rails PostgreSQL",
        "preferred_qualifications": "",
        "location": "Austin",
        "remote": "hybrid",
        "perks_and_benefits": "",
    }
    base.update(overrides)
    return base


def test_empty_title_blocks_even_if_confirmed() -> None:
    job = normalize_requirements(_job(title="  "))
    result = evaluate_gate(job, confirm_run_anyway=True)
    assert result.status == "blocked"
    assert result.gaps[0].field == "title"
    assert result.gaps[0].run_anyway_allowed is False


def test_short_title_blocks() -> None:
    job = normalize_requirements(_job(title="A"))
    result = evaluate_gate(job, confirm_run_anyway=False)
    assert result.status == "blocked"


def test_vague_only_must_haves_are_empty() -> None:
    assert must_haves_empty("good culture fit, team player, rockstar")
    assert must_haves_empty("a passionate ninja")
    assert not must_haves_empty("Ruby on Rails PostgreSQL")


def test_empty_must_haves_ignore_run_anyway() -> None:
    job = normalize_requirements(_job(requirements="good culture fit"))
    result = evaluate_gate(job, confirm_run_anyway=True)
    assert result.status == "blocked"
    assert any(gap.field == "requirements" for gap in result.gaps)


def test_missing_seniority_and_location_asks_first() -> None:
    job = normalize_requirements(_job(title="Rails Engineer", location="", remote=None))
    result = evaluate_gate(job, confirm_run_anyway=False)
    assert result.status == "needs_clarification"
    fields = {gap.field for gap in result.gaps}
    assert fields == {"seniority", "location"}
    assert all(gap.run_anyway_allowed for gap in result.gaps)


def test_run_anyway_records_assumptions() -> None:
    job = normalize_requirements(_job(title="Rails Engineer", location="", remote=None))
    result = evaluate_gate(job, confirm_run_anyway=True)
    assert result.status == "ok"
    assert result.assumptions == [ASSUMPTION_SENIORITY, ASSUMPTION_LOCATION]


def test_years_and_remote_phrase_skip_clarification() -> None:
    job = normalize_requirements(
        _job(
            title="Rails Engineer",
            description="5+ years building APIs. Work from home.",
            location="",
            remote=None,
        )
    )
    result = evaluate_gate(job, confirm_run_anyway=False)
    assert result.status == "ok"
    assert result.assumptions == []


def test_complete_req_is_ok() -> None:
    result = evaluate_gate(normalize_requirements(_job(title="Senior Rails Engineer")), confirm_run_anyway=False)
    assert result.status == "ok"


def test_title_and_field_caps() -> None:
    with pytest.raises(PayloadError):
        normalize_requirements(_job(title="x" * 201))
    with pytest.raises(PayloadError):
        normalize_requirements(_job(description="x" * 4001))


def test_blob_is_overridden_by_explicit_title() -> None:
    blob = parse_raw_blob("title: Junior Analyst\nrequirements: SQL Excel Python\n")
    merged = merge_requirements(blob, {"title": "Senior Analyst"})
    job = normalize_requirements(merged)
    assert job["title"] == "Senior Analyst"
    assert job["requirements"] == "SQL Excel Python"


def test_invalid_blob() -> None:
    with pytest.raises(PayloadError):
        parse_raw_blob("title: [unterminated")
    with pytest.raises(PayloadError):
        parse_raw_blob("- just a list")

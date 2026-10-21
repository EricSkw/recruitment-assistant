"""Scrape host policy and YAML crew contract."""

from recruitment.config_check import load_validated, write_prompt_trace
from recruitment.paths import PROMPT_TRACE_PATH
from recruitment.scrape_policy import scrape_refusal_reason


def test_scrape_refuses_linkedin_and_non_http() -> None:
    assert scrape_refusal_reason("https://www.linkedin.com/in/someone")
    assert scrape_refusal_reason("https://linkedin.com/jobs")
    assert scrape_refusal_reason("https://uk.linkedin.com/in/someone")
    assert scrape_refusal_reason("file:///etc/passwd")
    assert scrape_refusal_reason("https://example.com/profile") is None


def test_yaml_crew_contract_and_prompt_trace() -> None:
    agents, tasks = load_validated()
    assert set(agents) == {"researcher", "matcher", "communicator", "reporter"}
    assert tasks["compile_report"]["context"] == [
        "research_candidates",
        "match_and_score",
        "draft_outreach",
    ]
    assert agents["reporter"]["tools"] == []
    write_prompt_trace(agents, tasks)
    text = PROMPT_TRACE_PATH.read_text(encoding="utf-8")
    assert "Job Candidate Researcher" in text
    assert "OPENAI_API_KEY" not in text

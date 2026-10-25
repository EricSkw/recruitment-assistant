"""Crew object binds four agents, sequential process, and report context."""

from pathlib import Path

from recruitment.crew_runtime import build_crew


def test_build_crew_matches_sad(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.delenv("CREWAI_TRACING_ENABLED", raising=False)
    crew = build_crew(model="gpt-4o")
    assert crew.name == "recruitment"
    assert crew.tracing is True
    assert crew.process == "sequential"
    assert crew.memory is False
    assert crew.max_rpm == 20
    assert [agent.role for agent in crew.agents] == [
        "Job Candidate Researcher",
        "Candidate Matcher and Scorer",
        "Candidate Outreach Strategist",
        "Candidate Reporting Specialist",
    ]
    assert all(agent.allow_delegation is False for agent in crew.agents)
    assert all(agent.max_iter <= 12 for agent in crew.agents)
    assert all(agent.max_retry_limit >= 2 for agent in crew.agents)
    assert all(agent.max_execution_time == 150 for agent in crew.agents)
    names = [task.name for task in crew.tasks]
    assert names == [
        "research_candidates",
        "match_and_score",
        "draft_outreach",
        "compile_report",
    ]
    report = crew.tasks[-1]
    assert [task.name for task in report.context] == names[:3]
    assert report.guardrail is not None
    assert crew.agents[-1].tools == []
    tool_names = [tool.name for tool in crew.agents[0].tools]
    assert "public_website_scrape" in tool_names
    scrape = next(tool for tool in crew.agents[0].tools if tool.name == "public_website_scrape")
    refused = scrape._run(website_url="https://www.linkedin.com/in/someone")
    assert "not allowed" in refused

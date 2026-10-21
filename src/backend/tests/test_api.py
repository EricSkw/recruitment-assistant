"""API contract with a mocked kickoff. AC-001, AC-002, AC-008, AC-011."""

import threading
import time

from fastapi.testclient import TestClient

from recruitment.api import create_app
from recruitment.results import KickoffFailed, KickoffResult

KEYS = {"OPENAI_API_KEY": "test-openai", "SERPER_API_KEY": "test-serper"}

VALID = {
    "title": "Senior Rails Engineer",
    "description": "Build product APIs.",
    "responsibilities": "Ship features with the team.",
    "requirements": "Ruby on Rails PostgreSQL",
    "preferred_qualifications": "React",
    "location": "Austin",
    "remote": "hybrid",
    "perks_and_benefits": "",
}


def _client(runner, environ=None, wall_clock_s=5):
    app = create_app(
        runner=runner,
        environ=KEYS if environ is None else environ,
        wall_clock_s=wall_clock_s,
    )
    return TestClient(app)


def _wait(client: TestClient, run_id: str) -> dict:
    last = {}
    for _ in range(40):
        last = client.get(f"/api/runs/{run_id}").json()
        if last.get("status") in {"completed", "failed", "partial"}:
            return last
        time.sleep(0.05)
    raise AssertionError(last)


def test_health() -> None:
    client = _client(lambda inputs, on_task: KickoffResult("unused"))
    assert client.get("/health").json() == {"status": "ok"}


def test_missing_key_does_not_kickoff() -> None:
    called = {"value": False}

    def runner(inputs, on_task):
        called["value"] = True
        return KickoffResult("no")

    client = _client(runner, environ={"OPENAI_API_KEY": "", "SERPER_API_KEY": "x"})
    response = client.post("/api/runs", json={"job_requirements": VALID})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "MISSING_API_KEY"
    assert called["value"] is False


def test_empty_title_is_422() -> None:
    client = _client(lambda inputs, on_task: KickoffResult("no"))
    body = {"job_requirements": {**VALID, "title": " "}}
    response = client.post("/api/runs", json=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION"


def test_clarification_does_not_kickoff() -> None:
    called = {"value": False}

    def runner(inputs, on_task):
        called["value"] = True
        return KickoffResult("no")

    client = _client(runner)
    job = {**VALID, "title": "Rails Engineer", "location": None, "remote": None}
    response = client.post("/api/runs", json={"job_requirements": job})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "needs_clarification"
    assert payload["run_id"] is None
    assert called["value"] is False


def test_run_anyway_starts_crew_with_assumptions() -> None:
    seen = {}

    def runner(inputs, on_task):
        seen["inputs"] = inputs
        on_task("research_candidates")
        on_task("match_and_score")
        on_task("draft_outreach")
        on_task("compile_report")
        return KickoffResult(report_markdown="## Job requirements\n\nnot sent")

    client = _client(runner)
    job = {**VALID, "title": "Rails Engineer", "location": None, "remote": None}
    response = client.post(
        "/api/runs",
        json={"job_requirements": job, "confirm_run_anyway": True, "candidate_limit": 5},
    )
    assert response.status_code == 202
    run_id = response.json()["run_id"]
    body = _wait(client, run_id)
    assert body["status"] == "completed"
    assert "seniority unspecified" in body["assumptions"][0]
    assert "location unspecified" in body["assumptions"][1]
    assert seen["inputs"]["candidate_limit"] == "5"
    assert "seniority unspecified" in seen["inputs"]["assumptions"]
    assert "Rails Engineer" in seen["inputs"]["job_requirements"]


def test_phrase_confirmation_and_blob_override() -> None:
    seen = {}

    def runner(inputs, on_task):
        seen["inputs"] = inputs
        return KickoffResult("report")

    client = _client(runner)
    response = client.post(
        "/api/runs",
        json={
            "raw_blob": "run anyway",
            "job_requirements": {
                "title": "Rails Engineer",
                "requirements": "Ruby on Rails PostgreSQL",
            },
        },
    )
    assert response.status_code == 202
    _wait(client, response.json()["run_id"])
    assert "Ruby on Rails PostgreSQL" in seen["inputs"]["job_requirements"]


def test_busy_crew_returns_409() -> None:
    started = threading.Event()
    release = threading.Event()

    def runner(inputs, on_task):
        on_task("research_candidates")
        started.set()
        release.wait(5)
        return KickoffResult("done")

    client = _client(runner)
    first = client.post("/api/runs", json={"job_requirements": VALID})
    assert first.status_code == 202
    assert started.wait(2)
    second = client.post("/api/runs", json={"job_requirements": VALID})
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "CREW_BUSY"
    release.set()
    assert _wait(client, first.json()["run_id"])["status"] == "completed"


def test_guardrail_failure_is_partial() -> None:
    def runner(inputs, on_task):
        raise KickoffFailed("GUARDRAIL", "Report guardrail failed.", partial="partial text")

    client = _client(runner)
    response = client.post("/api/runs", json={"job_requirements": VALID})
    body = _wait(client, response.json()["run_id"])
    assert body["status"] == "partial"
    assert body["partial"] is True
    assert body["error"]["code"] == "GUARDRAIL"
    assert body["report_markdown"] == "partial text"


def test_timeout_names_last_task() -> None:
    def runner(inputs, on_task):
        on_task("draft_outreach")
        threading.Event().wait(2)
        return KickoffResult("late")

    client = _client(runner, wall_clock_s=0.3)
    response = client.post("/api/runs", json={"job_requirements": VALID})
    body = _wait(client, response.json()["run_id"])
    assert body["status"] == "failed"
    assert body["error"]["code"] == "TIMEOUT"
    assert "draft_outreach" in body["error"]["message"]
    time.sleep(0.4)
    again = client.get(f"/api/runs/{response.json()['run_id']}").json()
    assert again["status"] == "failed"


def test_unknown_run_and_limit() -> None:
    client = _client(lambda inputs, on_task: KickoffResult("x"))
    missing = client.get("/api/runs/not-a-run")
    assert missing.status_code == 404
    limited = client.post(
        "/api/runs",
        json={"job_requirements": VALID, "candidate_limit": 4},
    )
    assert limited.status_code == 422
    assert limited.json()["error"]["code"] == "VALIDATION"

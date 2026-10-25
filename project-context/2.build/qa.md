# QA — Recruitment Assistant

Smoke and acceptance check of the MVP chat flow. The crew is sequential CrewAI (`researcher`, `matcher`, `communicator`, `reporter`). The page at `http://127.0.0.1:5173/` submits to `POST /api/runs` and polls `GET /api/runs/{run_id}`.

**Result:** the clarify-before-kickoff path and the chat states pass. A completed recruiter report was shown in the browser only against a local mock of the run API. No live Grok or Serper kickoff was run. **AC-009 fails** because `.env.example` contains a non-placeholder `XAI_API_KEY`.

`@security.eng` should run before Deliver. Example config sets `security.require_security_assessment: true`, and `project-context/2.build/security.md` does not exist.

## Diagnostic

`project-context/2.build/setup.md` is not in the repository. QA continued because the PRD, SAD, frontend, backend, and integration artifacts already define the chat contract, and the test suites run from `src/backend` and `src/frontend`. No product behavior was added to fill that gap.

## Actions

| Action | Result |
|--------|--------|
| `*test-unit` | Backend gate, rubric, guardrail, YAML contract, crew build, and provider switch. 23 pytest cases, all passed |
| `*test-integration` | Backend API suite (14) and frontend fetch client (5). All passed. `tsc --noEmit` passed |
| `*qa` | Live gate smoke plus a mocked happy-path chat session |
| `*verify-flow` | Browser session on `http://127.0.0.1:5173/` against the live API, then against a QA mock on port 8000 |
| `*log-defects` | Defects and known gaps below |
| `*future-work` | Deferred checks below |

## Acceptance map

| ID | Result | Evidence |
|----|--------|----------|
| AC-001 | Pass | Empty title is `422` `VALIDATION` on the live API and in the chat. Pytest `test_empty_title_is_422`, `test_empty_title_blocks_even_if_confirmed` |
| AC-002 | Pass, mocked | `test_build_crew_matches_sad` and `test_yaml_crew_contract_and_prompt_trace`: four tasks, report context is research, match, and outreach. Not observed on a live kickoff |
| AC-003 | Not exercised live | Scrape refusal of `linkedin.com` is unit-tested. No live search result was inspected for invented contacts |
| AC-004 | Partial | Rubric weights sum to 100 (`test_rubric_sums_to_100`). A live ranked report was not produced |
| AC-005 | Partial | Mocked report and guardrail require “not sent”. No send route exists (`POST /api/send` is 404). A live communicator draft was not produced |
| AC-006 | Partial | Chat rendered the mocked report as headings, with Copy and Download `.md`. The body did not start with a code fence. Guardrail unit tests cover the heading list. Clipboard write failed in this browser |
| AC-007 | Pass | Banner: “Recommendations require human review. This app does not reject or contact candidates.” Footer: outreach drafts are never sent. `POST /api/reject`, `/api/advance`, and `/api/ats` are 404 |
| AC-008 | Pass in tests | `test_guardrail_failure_is_partial`, `test_timeout_names_last_task`, `test_missing_key_does_not_kickoff`. The browser error session was a validation error, not a timeout or missing key |
| AC-009 | Fail | `.env.example` is tracked and its `XAI_API_KEY` value is not a placeholder. It matches the operator `.env`. Prompt trace and `trace.log` do not contain the key values. `LINKEDIN_COOKIE` is not required |
| AC-010 | Pass, with a mock for completed | Empty, needs-clarification, error, in-progress, and completed were all visible in the chat. Completed used the QA mock, not the crew |
| AC-011 | Pass | Live API and chat: missing seniority and location return `needs_clarification`, `run_id` null, and “The crew was not started.” Vague must-haves stay `422` even with run anyway. Run anyway was not clicked |
| AC-012 | Pass in tests only | `test_run_anyway_starts_crew_with_assumptions` puts the two assumption strings on the crew input. The browser did not confirm run anyway, so no report Assumptions subsection was produced by the crew |
| AC-013 | Pass for the runtime contract | Unbound LinkedIn cookie / Selenium / send-mail snippets are rejected by the YAML check. Missing keys fail closed in tests. This QA pass did not halt on a missing setup file; that gap is recorded here |

## Unit

Command: `src/backend` with the repo virtualenv, `python -m pytest`. **37 passed**, 15 warnings, 5.94s (2026-10-24). The 23 unit cases are the modules below. Warnings are CrewAI deprecations (`function_calling_llm`, lock store) and the known note that function callbacks cannot be serialized.

| Module | Cases | What it locks |
|--------|------:|---------------|
| `tests/test_gate.py` | 11 | AC-011 empty title, short title, vague must-haves, run anyway ignored on hard blocks, seniority and location, assumption strings, years/remote skip, field caps, YAML override, invalid blob |
| `tests/test_guardrail.py` | 4 | Rubric total 100; required headings; leading code fence rejected; missing “not sent” rejected |
| `tests/test_contract.py` | 2 | LinkedIn and non-HTTP scrape refusal; four agents, report context, forbidden tool snippets, prompt trace |
| `tests/test_crew_build.py` | 1 | Sequential process, `memory` false, `max_rpm` 20, report `context`, scrape refusal of `https://www.linkedin.com/in/someone` |
| `tests/test_llm_config.py` | 5 | Default OpenAI, Grok base URL and `XAI_API_KEY`, alias vs `XAI_API_KEY`, unknown provider |

No application source file under `src/` exceeds the example config cap of 400 lines.

## Integration

Same pytest process. Frontend: `src/frontend` `vitest run` — **5 passed**. `tsc --noEmit` passed.

| Check | AC | Result |
|-------|----|--------|
| `GET /health` stays ok | — | Pass (`test_health`) |
| Missing selected key or Serper key does not call kickoff | AC-008, AC-009 | Pass |
| Grok does not require `OPENAI_API_KEY`; Grok without `XAI_API_KEY` is `503` | AC-009 | Pass |
| Unknown `LLM_PROVIDER` is `503` `CREW_FAILURE` | AC-008 | Pass |
| Empty title `422`; clarification does not call kickoff | AC-001, AC-011 | Pass |
| Run anyway and the exact `run anyway` blob start the crew with assumption strings | AC-012 | Pass, crew mocked |
| Second run `409` `CREW_BUSY` | NFR-003 | Pass |
| Guardrail failure is `partial`; timeout names the last task id | AC-008 | Pass, crew mocked |
| Unknown id `404` with message `Unknown run id.`; `candidate_limit` 3 is `422` | — | Pass |
| Vite origin preflight allowed; another origin is not | — | Pass |
| Frontend client: `202`, clarification, `422`, `409`, `503`, poll, unknown id, unreachable API | AC-010, AC-011 | Pass (`src/frontend/src/api/client.test.ts`) |

Live calls from this session, real API on `127.0.0.1:8000`, Vite proxy on `127.0.0.1:5173`:

| Request | HTTP | Body |
|---------|-----:|------|
| `GET /health` and `GET http://127.0.0.1:5173/health` | 200 | `{"status":"ok"}` |
| Empty title, `confirm_run_anyway: true` | 422 | `VALIDATION`, title must be at least 2 characters |
| Title and must-haves, no seniority, no location | 200 | `needs_clarification`, `run_id` null, both gaps `run_anyway_allowed: true` |
| Vague must-have “good culture fit”, run anyway set | 422 | Must-haves empty after the vague-phrase strip |
| `candidate_limit` 3 | 422 | `VALIDATION`, minimum 5 |
| Unknown run id | 404 | `VALIDATION`, `Unknown run id.` |
| `POST /api/send`, `/api/reject`, `/api/advance`, `/api/ats` | 404 | No decision or send API |

Access log shows those posts as 422 or 200. No `202` was issued against the real API. `trace.log` has no run line from this live process.

## Smoke

SAD §9 asks for one happy-path UI session against mocks or a fixture, one clarification session, and one error session.

### Empty, error, and clarification (live API)

Browser: `http://127.0.0.1:5173/`.

| Step | Observed |
|------|----------|
| Load | Status “No run yet.” Human-review banner is visible. Fixture preview control is gone. Candidate count defaults to 10 |
| Send with empty fields | User line appears before the response. Then `VALIDATION` for empty title and empty must-haves. Retry and Edit requisition are shown. Send is enabled again |
| Title “Backend Engineer”, must-haves “Python FastAPI PostgreSQL”, description and responsibilities filled, location and remote left blank | “The crew was not started.” Gaps name seniority and location. Both say run anyway is allowed. Status: “Needs clarification. The crew has not started.” Form text remains. Run anyway was not clicked |

### Happy path (QA mock, not the crew)

The real API was stopped. A process-local mock on port 8000 answered `202`, then polled through `research_candidates`, `match_and_score`, `draft_outreach`, and `compile_report`, then `completed`. The chat page was not modified.

| Step | Observed |
|------|----------|
| Fill example requisition | Title “Senior Backend Engineer”, must-haves “Python, FastAPI, PostgreSQL”, location Lisbon, remote Hybrid |
| Send | User line is in the transcript while Send is disabled. Status later read “Running draft_outreach — Recommender (communicator).” |
| Second `POST /api/runs` during that run | `409` `CREW_BUSY` |
| Terminal poll | Status “Completed.” Rendered headings: Job requirements, Assumptions, Candidate profiles, Ranked scores and justifications, Outreach drafts, Sources, Recommendations for recruiter review. Lead is Fixture Lead A with `https://example.com/fixture-lead-a` and contact unverified. Score 72. Text says the drafts were not sent and that review is required |
| Copy | Button is present. This browser returned “Copy failed. Use download.” |
| Download `.md` | Button is present. The file save was not confirmed |

The mock report is layout text. It is not a sourcing result and not a hiring decision.

The real API was started again on `127.0.0.1:8000` after the mock was stopped. The Vite dev server on `127.0.0.1:5173` was already running and was left running.

## Defects

1. **AC-009 — secret material in `.env.example`.** The tracked example file sets `XAI_API_KEY` to a 102-character value that is not a placeholder and is the same value as the operator `.env`. The value is not copied here. Treat the key as exposed, rotate it at the provider, and replace the example entry with an empty placeholder. `OPENAI_API_KEY` in the example is still the placeholder `your_openai_api_key_here`. `SERPER_API_KEY` in the example is empty.

## Known gaps

1. No live crew run. AC-003, AC-004, AC-005, and AC-012 are not proven against Grok or Serper. Run anyway was offered and not used.
2. Clipboard write failed in the automation browser. Download was not confirmed. A normal browser session should retry both.
3. `setup.md` is still absent.
4. `frontend.md` still describes the fixture client. `integration.md` is the wired description.
5. Missing keys are reported before the clarify gate, so a recruiter with a bad `.env` sees `503` `MISSING_API_KEY` instead of the gap list. The API process must be restarted after `.env` changes. This matches `backend.md`.
6. Run state is in process memory. A restart makes an old poll `404` `Unknown run id.`
7. Closing the page does not cancel a kickoff.
8. FastAPI does not serve `src/frontend/dist/`. Local use is two processes.
9. CrewAI logs that function callbacks cannot be serialized. `/health` still returns ok.
10. The hours-saved KPI is defined in the PRD (§7) and is not a CI assertion. No operator diary was checked.
11. `aamad.config.yml` is absent. Example testing preferences were applied: unit tests, integration tests, and acceptance-criteria mapping.

## Future work

- One operator requisition with real `XAI_API_KEY` and `SERPER_API_KEY`, after the example-file key is rotated. Expect at least one `source_url` or an explicit empty or partial Diagnostic, and no invented email or phone.
- Confirm run anyway on a live report and check the Assumptions subsection (AC-012).
- Browser confirmation of Copy and Download `.md`.
- UI session for `503` `MISSING_API_KEY` and for `TIMEOUT` naming the last task id.
- NFR-001 (kickoff within 8 minutes) and NFR-002 (submit acknowledged within 2 seconds) as timed checks. This pass only observed that the user line paints before the HTTP response returns.
- P1: task streaming, last-N local history, PDF export.
- P2: people-search APIs, ATS export, send, SSO. Not in this build (`nonmvp.py`).
- Security assessment (`@security.eng`), including the `.env.example` key, trace redaction, and the LinkedIn scrape denylist.
- Jurisdiction banner remains out of scope (SAD Open Question 3).

## Sources

1. `project-context/1.define/prd.md` (product-mgr, 2026-10-16), P0-1–P0-11, AC-001–AC-013.
2. `project-context/1.define/sad.md` (system-arch, 2026-10-19), §2 gate, §3 states, §4 API, §9 testing. No user-story files; PRD acceptance criteria are the anchors.
3. `project-context/2.build/frontend.md` (frontend-eng, 2026-10-23). Stale on the fixture client.
4. `project-context/2.build/backend.md` (backend-eng), gate, crew, and error envelope.
5. `project-context/2.build/integration.md` (integration-eng, 2026-10-23), wired client and known issues.
6. `.cursor/agents/qa-eng.md` actions `test-unit`, `test-integration`, `qa`, `verify-flow`, `log-defects`, `future-work`.
7. `aamad.config.example.yml`. No project `aamad.config.yml`.
8. `.env.example` names. The secret value was not written into this artifact.

## Assumptions

- Missing `setup.md` does not change the pass/fail of the checks above.
- A happy path against a local mock satisfies SAD §9 “mocks or a recorded fixture.” It does not satisfy the pilot line that asks for a real requisition run.
- Resolved `AAMAD_TARGET_RUNTIME` is `crewai` from the PRD, SAD, and `.env.example`.
- This persona made no model call. Prompt Trace was not written for that reason.
- Linux Node at `/usr/bin/node` (v18.19.1) ran Vitest and `tsc`. The Windows `npm` on `PATH` was not used.
- The QA mock listened on port 8000 only while the real API was stopped, and it was not left running.

## Open Questions

1. `setup.md` now records the environment. `src/frontend` plus `src/backend` is the accepted scaffold.
2. After the `XAI_API_KEY` in `.env.example` is rotated, who runs the first live requisition: the operator, or a later QA pass?
3. Should a missing key be reported after the clarify gate so gaps stay visible? Current code checks keys first.
4. Is clipboard failure limited to this automation browser? Confirm on the operator’s browser before calling AC-006 fully passed.

## Audit

- **timestamp:** 2026-10-24T03:19:21Z
- **persona id:** `qa-eng`
- **action:** `test-unit`, `test-integration`, `qa`, `verify-flow`, `log-defects`, `future-work`
- resolved AAMAD_TARGET_RUNTIME: `crewai` (PRD, SAD, `.env.example`)
- **llm / temperature / max_tokens:** none for this persona. No model call. Prompt Trace omitted for that reason
- **tools:** read PRD, SAD §9, frontend.md, backend.md, integration.md, qa persona, example config; `pytest` (37 passed); `vitest` (5 passed); `tsc --noEmit`; live `GET /health` and `POST /api/runs`; browser session on `http://127.0.0.1:5173/`; temporary mock on port 8000, then the real API restored
- **outputs:** this artifact

# Backend — Recruitment Assistant

MVP backend for the sequential recruitment crew. The HTTP API accepts a job requisition, applies the clarify-before-kickoff gate, and runs one CrewAI crew off the request thread.

Operator names map to the PRD quartet (SAD AD-02). They are not collapsed into three agents.

| Request name | Agent id | Role |
|--------------|----------|------|
| Researcher | `researcher` | Job Candidate Researcher |
| Evaluator | `matcher` | Candidate Matcher and Scorer |
| Recommender | `communicator` | Candidate Outreach Strategist (drafts only) |
| Recommender | `reporter` | Candidate Reporting Specialist (compiled report) |

## Diagnostic

`project-context/2.build/setup.md` is not in the repository. `@project.mgr` has not recorded the environment scaffold. Implementation continued because the operator invoked `*develop-be` and the PRD plus SAD already specify the crew, the gate, the rubric, and the HTTP contract. No application requirement was invented to fill that gap.

CrewAI writes its own data directory on import (`appdirs` user data). Product runs keep `memory=False` and do not set `CREWAI_STORAGE_DIR`.

## Actions

| Action | Result |
|--------|--------|
| `*develop-be` | Python package `src/backend/recruitment`, FastAPI app, dependencies in `src/backend/requirements.txt` |
| `*define-agents` | `src/backend/config/agents.yaml`, `src/backend/config/tasks.yaml`, entrypoint `src/backend/crew.py` |
| `*implement-endpoint` | `GET /health`, `POST /api/runs`, `GET /api/runs/{run_id}` |
| `*stub-nonmvp` | `src/backend/recruitment/nonmvp.py` raises `NotImplementedError` for history, token streaming, PDF, send, ATS, and login |
| `*document-backend` | This file |

## Runtime

Resolved `AAMAD_TARGET_RUNTIME`: `crewai`.

Process is sequential. `allow_delegation` is false on every agent. `memory` is false. One shared LLM is used for the whole process. `LLM_PROVIDER` selects it: `openai` (default) or `grok`. Tool mode stays on CrewAI’s default function calling. `function_calling_llm` is not set, so the run does not switch mode.

| `LLM_PROVIDER` | Key | Model env | Default model | Endpoint |
|----------------|-----|-----------|---------------|----------|
| `openai` | `OPENAI_API_KEY` | `OPENAI_MODEL` | `gpt-4o` | OpenAI |
| `grok` | `XAI_API_KEY` (`GROK_API_KEY` is an alias) | `GROK_MODEL` | `grok-4.7` | `https://api.x.ai/v1` |

Only the selected provider’s key is required. The other key may stay empty. An unknown `LLM_PROVIDER` returns `503` `CREW_FAILURE`. Temperature `0.2` and `max_tokens` `8192` apply to both. Restart the process after changing the provider. Create the Grok key at [console.x.ai](https://console.x.ai/) (API Keys).

| Control | Value | Where |
|---------|-------|-------|
| `max_iter` | 12 | each agent |
| `max_retry_limit` | 2 | each agent (CrewAI agent field) |
| `guardrail_max_retries` | 2 | each task (CrewAI’s task retry field; SAD `max_retry_limit`) |
| `max_execution_time` | 150 seconds | each agent |
| `max_rpm` | 20 | crew |
| Kickoff wall clock | 480 seconds | `RunService` around the worker |
| `temperature` | 0.2 | crew LLM |
| `max_tokens` | 8192 | crew LLM |
| Candidate N | 5–10, default 10 | request or `CANDIDATE_LIMIT` |

## Crew

YAML is the source for role, goal, backstory, task description, and expected output. `src/backend/recruitment/crew_runtime.py` loads that YAML, checks the tool ids and the task graph, and builds the crew.

| Order | Task id | Agent | Context |
|-------|---------|-------|---------|
| 1 | `research_candidates` | `researcher` | none |
| 2 | `match_and_score` | `matcher` | research |
| 3 | `draft_outreach` | `communicator` | research, match |
| 4 | `compile_report` | `reporter` | research, match, outreach |

Tools bound in Python, named in YAML:

- `serper_search` — `SerperDevTool` (`SERPER_API_KEY`)
- `public_scrape` — scrape wrapper. Allows `http` and `https`. Refuses `linkedin.com`, `www.linkedin.com`, and any host ending in `.linkedin.com`. Drops cookies and `Authorization`.
- `reporter` has no tools.

Search hits may still cite a public LinkedIn URL as `source_url`. That citation is not a scraped profile. The wrapper does not fetch the page.

`compile_report` uses `report_guardrail`: required headings, body does not start with a code fence, and the text contains “not sent”. On failure CrewAI retries up to `guardrail_max_retries`, then the run is `partial` or `failed` with code `GUARDRAIL`. The API does not rewrite the report.

Scoring rubric (recommendations, not decisions): skills match 0–40, seniority fit 0–20, evidence quality 0–25, location or remote fit 0–15. Total 100. Unverified evidence is capped at 5. Omitted seniority or location scores 0 and is labeled not assessed. The rubric is in the matcher prompt and in `recruitment/rubric.py`.

Prompt templates, before kickoff interpolation, are written to `logs/prompt-trace.md`. Kickoff inputs are not copied into that file. Lifecycle lines (run id, task, error code, token count, search-call count) go to stdout and `logs/trace.log`. Values of `OPENAI_API_KEY`, `XAI_API_KEY`, `GROK_API_KEY`, and `SERPER_API_KEY` are redacted when they appear in a log line.

## Clarify-before-kickoff gate

`recruitment/gate.py` runs in the API before `kickoff`. It does not call an LLM.

Hard block (`422`, code `VALIDATION`). `confirm_run_anyway` is ignored.

- Title missing or shorter than 2 characters after trim.
- Must-haves empty after the vague-phrase strip. Fewer than 3 alphanumeric tokens that are not the SAD stopwords counts as empty.

Clarify (`200`, `needs_clarification`, `run_id` null). No kickoff.

- Seniority missing from title, description, responsibilities, and requirements.
- Location missing: empty `location`, empty `remote`, and the same text lacks the location lexicon.

“Run anyway” is `confirm_run_anyway: true`, or `raw_blob` whose trimmed text equals `run anyway`. A bare yes is not confirmation. The client resubmits the same fields with that flag. The API does not store the previous payload to compare it. When the run is allowed, the crew input `assumptions` is:

- `seniority unspecified; matcher must mark seniority fit as not assessed`
- `location unspecified; search the public web without a geography penalty`

If there is no gap, the crew input is the string `None`.

`raw_blob`, when it is not the confirmation phrase, is parsed as YAML. Explicit JSON fields override blob keys. Serialized job JSON is capped at 12 000 characters. Title is capped at 200 characters. Each other text field is capped at 4 000.

## API

Local base URL: `http://127.0.0.1:8000`. JSON, UTF-8. No token streaming.

`GET /health` → `200` `{"status":"ok"}`. This stays up when keys or YAML are bad.

`POST /api/runs`

- `202` `{"run_id","status":"queued","gaps":[]}` after the gate passes. Kickoff runs on a worker thread.
- `200` needs clarification. `run_id` is null.
- `422` schema error or hard block. Envelope code `VALIDATION`.
- `409` another run is `queued` or `running`. Code `CREW_BUSY`. The check and the insert share one lock.
- `503` missing the selected LLM key (`OPENAI_API_KEY` or `XAI_API_KEY`) or `SERPER_API_KEY`. Code `MISSING_API_KEY`. Checked on every POST, including clarification, so a run cannot start without keys.
- `503` `LLM_PROVIDER` is not `openai` or `grok`. Code `CREW_FAILURE`.
- `503` YAML or tool binding failed at startup. Code `CREW_FAILURE`.

`GET /api/runs/{run_id}` → `200` with `status` (`queued`, `running`, `completed`, `failed`, `partial`), `current_task`, `partial`, `assumptions`, `report_markdown`, `error`. Unknown id → `404`. The published error-code list has no `NOT_FOUND` value, so the envelope uses `VALIDATION` and the message `Unknown run id.`

Error envelope:

```json
{"error": {"code": "VALIDATION | MISSING_API_KEY | CREW_BUSY | TIMEOUT | CREW_FAILURE | GUARDRAIL", "message": "operator-safe string", "run_id": "uuid or null"}}
```

On `TIMEOUT`, the message names the last task id. A late worker cannot overwrite a terminal status. If a crew exception happens after a task produced text, status is `partial`, `partial` is true, and `report_markdown` is that labeled text. Otherwise status is `failed` and nothing is invented.

Completed markdown is also written to `var/runs/{run_id}.md` (gitignored). The in-memory map is dropped on process exit. That file is the operator copy for the current process, not a candidate database and not last-N history.

There is no reject, advance, or send endpoint.

Cancellation: a client disconnect does not stop the in-process crew. The operator restarts the process. Queueing is deferred.

## Files

| Path | Purpose |
|------|---------|
| `src/backend/config/agents.yaml` | Four agents |
| `src/backend/config/tasks.yaml` | Four tasks and context |
| `src/backend/crew.py` | Entrypoint re-export of `build_crew` and `kickoff` |
| `src/backend/main.py` | Uvicorn on `HOST` / `PORT` (default `127.0.0.1:8000`) |
| `src/backend/recruitment/asgi.py` | Application object for Uvicorn |
| `src/backend/recruitment/llm_config.py` | `LLM_PROVIDER` switch: OpenAI or Grok |
| `src/backend/recruitment/gate.py` | Gate |
| `src/backend/recruitment/crew_runtime.py` | Crew build and kickoff |
| `src/backend/recruitment/tools.py` | Search counter and scrape refusal |
| `src/backend/recruitment/guardrail.py` | Report headings |
| `src/backend/recruitment/runs.py` | One active run, 480s supervisor |
| `src/backend/recruitment/nonmvp.py` | Deferred and forbidden stubs |
| `src/backend/requirements.txt` | Pinned direct dependencies |
| `src/backend/tests/` | Gate, rubric, guardrail, YAML contract, mocked API, crew construction |

## How to run

From `src/backend/`, with the repo virtualenv:

```bash
../../.venv/bin/pip install -r requirements.txt
../../.venv/bin/python -m pytest
../../.venv/bin/python main.py
```

Put real keys in the repo `.env` (not in git). Set `LLM_PROVIDER` to `openai` or `grok`. Names are listed in `.env.example`. The example placeholder `your_openai_api_key_here` is not treated as missing; the provider will fail the run if it is not a real key.

## Tests

`cd src/backend && ../../.venv/bin/python -m pytest` — 28 passed on 2026-10-19. The package now lives under `src/backend`.

| Test module | What it locks |
|-------------|----------------|
| `test_gate.py` | AC-011 empty title, vague must-haves, seniority, location, run anyway, field caps, YAML override |
| `test_guardrail.py` | Rubric total 100; report headings, fence, “not sent” |
| `test_contract.py` | YAML agent set, report context, forbidden tool snippets, prompt trace |
| `test_api.py` | Health, missing key, empty title, clarification without kickoff, assumptions on the crew input, `409`, partial guardrail, timeout, unknown id |
| `test_crew_build.py` | Four agents, sequential, `memory` false, `max_rpm` 20, report `context`, scrape refusal of `linkedin.com` |

Live OpenAI and Serper calls are not part of this suite.

## Non-MVP

Not implemented, and not callable from the routes: last-N report history, token streaming, PDF export, outreach send, ATS export, operator login. See `nonmvp.py`.

## Sources

1. `project-context/1.define/prd.md` (product-mgr, 2026-10-16), especially §3 agents, P0-1–P0-9, P0-11, NFR-001–NFR-003, NFR-011.
2. `project-context/1.define/sad.md` (system-arch, 2026-10-19), §2 crew and gate, §4 API, AD-02, AD-03, AD-05, AD-06, AD-09, AD-10.
3. `.cursor/agents/backend-eng.md` actions `develop-be`, `define-agents`, `implement-endpoint`, `stub-nonmvp`, `document-backend`.
4. `.cursor/rules/adapter-crewai.mdc` and `.cursor/rules/aamad-core.mdc`.
5. `aamad.config.example.yml` (no project `aamad.config.yml`): type checking, 400-line file cap, unit and integration tests.
6. `.env.example` names. This change adds `SERPER_API_KEY`, `CANDIDATE_LIMIT`, `HOST`, and `PORT` with empty or non-secret defaults.
7. Installed libraries used for signatures: `crewai==1.15.28`, `crewai-tools==1.15.28`, `fastapi==0.149.0`.

## Assumptions

- Missing `setup.md` does not change the SAD contract. Backend added the `.env.example` names SAD §4 assigned to setup.
- No `aamad.config.yml`. Example preferences apply. PRD and SAD stay authoritative.
- Evaluator is `matcher`. Recommender is `communicator` plus `reporter` (SAD AD-02).
- Any host equal to `linkedin.com` or ending in `.linkedin.com` is refused by the scrape tool, including the two hosts named in the SAD.
- “Run anyway” is stateless: the client resubmits the normalized fields with the flag or the exact `raw_blob` phrase. The API does not remember the prior body.
- CrewAI’s task retry field is `guardrail_max_retries`. It is set to 2 to match SAD `max_retry_limit`. Agent `max_retry_limit` is also 2.
- `GET` of an unknown run uses error code `VALIDATION` because the SAD code list has no separate not-found code. HTTP status remains 404.
- A blank required key for the selected provider fails closed. The sample OpenAI placeholder in `.env.example` is only a placeholder.
- `LLM_PROVIDER` defaults to `openai`. `grok` calls the xAI OpenAI-compatible chat API at `https://api.x.ai/v1` with default model `grok-4.7` (xAI docs, retrieved 2026-10-21). `GROK_API_KEY` is accepted when `XAI_API_KEY` is empty.
- Default `candidate_limit` comes from `CANDIDATE_LIMIT` when the request omits it, then 10. Values outside 5–10 are `422`.
- Completed reports may be written under `var/runs/`. Last-N history remains P1.
- Function-calling tool mode is CrewAI’s default for these tools. It is not switched during a run.
- Prompt trace stores YAML templates only, not the recruiter’s requisition text.

## Open Questions

1. `setup.md` now records the environment and accepts `src/backend` as the scaffold.
2. SAD Open Question 5: search vendor is implemented as Serper (`SERPER_API_KEY`). Confirm before replacing the tool class.
3. Should `POST /api/runs` return `needs_clarification` when API keys are missing, instead of `503`? This build follows SAD §4: every accepting POST fails closed with `MISSING_API_KEY`.
4. CrewAI warns that task callbacks are not checkpoint-serializable. MVP does not resume from checkpoints. No change unless a later epic enables them.
5. Jurisdiction banner, people-data APIs besides Serper, and `aamad.config.yml` remain the SAD open questions. They are out of this epic.

## Audit

- **timestamp:** 2026-10-19T22:22:06Z
- **persona id:** `backend-eng`
- **action:** `develop-be`, `define-agents`, `implement-endpoint`, `stub-nonmvp`, `document-backend`
- resolved AAMAD_TARGET_RUNTIME: `crewai` (PRD, SAD, `.env.example`; shell export was not required)
- **llm / temperature / max_tokens:** `LLM_PROVIDER` `openai` or `grok`; OpenAI model `gpt-4o` via `OPENAI_MODEL`; Grok model `grok-4.7` via `GROK_MODEL` and base URL `https://api.x.ai/v1`; temperature `0.2`; `max_tokens` `8192`; `max_rpm` `20`; `max_iter` `12`; agent `max_retry_limit` `2`; task `guardrail_max_retries` `2`; agent `max_execution_time` 150s; kickoff wall clock 480s; `memory=False`; function-calling tool mode fixed
- **revision:** 2026-10-21T14:20:00Z — operator request: configurable OpenAI or Grok API key (`LLM_PROVIDER`)
- **Prompt Trace:** `logs/prompt-trace.md` (YAML templates). Per-run lifecycle: stdout and `logs/trace.log`
- **tools:** read PRD, SAD, backend persona, CrewAI adapter; `pip install` of the pins in `src/backend/requirements.txt`; `pytest` (28 passed)
- **outputs:** `src/backend/` package and this artifact
- **libraries:** crewai 1.15.28, crewai-tools 1.15.28, fastapi 0.149.0, uvicorn 0.54.0, pydantic 2.12.5

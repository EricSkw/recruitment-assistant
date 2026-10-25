# System Architecture Document — Recruitment Assistant (MVP)

**PRD**: `project-context/1.define/prd.md`  
**MRD**: `project-context/1.define/mrd.md`  
**User Stories**: N/A (no files under `project-context/1.define/user-stories/`)  
**Context summary**: `project-context/1.define/context-summary.md`  
**MVP Scope**: Chat-operated sequential crew that researches public candidate leads, scores them, drafts outreach templates, and returns one recruiter report. Assistive only.  
**Selected Runtime**: `crewai`  
**Adapter**: `.cursor/rules/adapter-crewai.mdc`

---

### 1. MVP Architecture Philosophy & Principles

**MVP Design Principles**:

- Recruiter feedback first: the first usable run is a sourced shortlist plus copy-ready drafts the operator can accept or ignore.
- Minimal agent set: four sequential specialists, no manager, no delegation, no memory.
- Observable by default: health endpoint, run id, task lifecycle, and redacted error logs.
- Deploy scaffolding is configuration and a runbook in Deliver; this SAD does not authorize a live deploy.
- Do not invent job requirements, contacts, or hiring outcomes. Gaps are clarified, labeled as Assumptions, or blocked.

**Core vs Future Features**:

- **MVP**:
  - Job-requirement intake (paste or short form) with a deterministic clarify-before-kickoff gate (PRD P0-1, P0-11).
  - One sequential CrewAI kickoff: researcher → matcher → communicator → reporter (P0-2).
  - Public-web leads with `source_url` or `unverified` (P0-3). Default candidate count **10**, allowed range **5–10**.
  - Numeric scores and written justifications against the rubric in §2 (P0-4).
  - Outreach **templates only**; UI and report state they were not sent (P0-5, P0-7).
  - One markdown report in the chat transcript with copy/download (P0-6).
  - Run status, partial labeling, and Diagnostic on failure (P0-8).
  - Secrets from environment only (P0-9).
  - Minimal single-page web chat (P0-10).
- **Future** (PRD P1/P2; do not build in the MVP epics):
  - P1: adjustable N and location already allowed on the request; lasting local history of the last N reports; token streaming; PDF export.
  - P2: people-search or job-board APIs, ATS export, recruiter-OAuth send, multi-user auth/SSO/RBAC, bias-audit packs, job-seeker reverse matching, hierarchical crew, memory, `kickoff_for_each`, interview scheduling, emotion or personality inference (prohibited direction).
- **Explicit exclusions**:
  - LinkedIn cookie, `LI_AT`, `LINKEDIN_COOKIE`, Selenium login, or fetching `linkedin.com` with the scrape tool.
  - Email, InMail, or any send-mail tool.
  - Auto-reject, auto-advance, or candidate-facing “not qualified” notices.
  - Durable shared candidate database.
  - CLI as the primary interface (a developer may still call the API; the product surface is the web chat).

**Technical Architecture Decisions**:

| ID | Decision | Rationale | Trace |
|----|----------|-----------|-------|
| AD-01 | Runtime `crewai`, sequential process, YAML agents/tasks | PRD selected runtime; adapter forbids hierarchical MVP; example workflow is sequential | PRD §3, adapter-crewai |
| AD-02 | Four agents: `researcher`, `matcher`, `communicator`, `reporter` | PRD core definitions and AC-002. Operator shorthand “Evaluator” is `matcher`. “Recommender” is the pair `communicator` (drafts) + `reporter` (compiled recommendations). Do not collapse to three agents. | PRD §3 |
| AD-03 | FastAPI backend, Python | PRD: Python backend. FastAPI gives typed schemas and a fast accept path while the crew runs off the request thread. | PRD §8, §3 |
| AD-04 | Vite + React + TypeScript single-page chat | PRD requires a web chat, system theme, minimal style, type checking. No vendor component library. One route. Backend wiring is the integration epic’s job; this SAD defines the contract. | PRD §6, example config `ui` |
| AD-05 | Non-streaming report; poll task status | P0 batch report is enough (PRD Open Question 6). NFR-002 is met by acknowledging submit within 2 seconds. Task name is exposed by poll so the UI can show which agent is running. Token streaming is P1. | NFR-002, P0-10, P1 |
| AD-06 | No database | NFR-007. In-memory run record for the process lifetime. Optional gitignored file under `var/runs/` is an operator export of the report, not a CRM. | NFR-007, PRD integrations |
| AD-07 | Pre-kickoff gate in the API, not an LLM | AC-011 forbids kickoff on empty title or empty must-haves. A deterministic parser avoids spending tokens to invent a spec. Heuristic is specified in §2. | P0-11, PRD Open Question 9 |
| AD-08 | Bind `127.0.0.1`, no login | PRD AuthN/Z: local single operator. Exposing the port is an operator risk, not an MVP feature. | PRD integrations |
| AD-09 | One crew LLM per process: `LLM_PROVIDER=openai` (default `gpt-4o`) or `LLM_PROVIDER=grok` (default `grok-4.7` at `https://api.x.ai/v1`) | Operator request 2026-10-21. Temperature stays `0.2`. The selected provider’s key is required; the other key may be empty. Do not switch provider or tool mode mid-run. | PRD Assumptions, operator request |
| AD-10 | Outer kickoff budget 480s; `max_rpm=20` | NFR-001 P95 target ≤ 8 minutes. Crew-level RPM caps cost. Details in §2 and §7. | NFR-001, adapter |

---

### 2. Multi-Agent System Specification

**Agent Architecture Requirements**:

Crew id: `recruitment`. Process: `Process.sequential`. `memory=False`. `allow_delegation=false` on every agent. No hierarchical manager.

| Agent id | Role (PRD) | Goal | Tools | Notes |
|----------|------------|------|-------|-------|
| `researcher` | Job Candidate Researcher | Find up to N potential candidates from public web resources | `SerperDevTool`, `ScrapeWebsiteTool` | No LinkedIn cookie/Selenium. Scrape tool must refuse `linkedin.com` and non-public URLs. |
| `matcher` | Candidate Matcher and Scorer | Score candidates against the written requisition and recruiter-confirmed Assumptions | `SerperDevTool`, `ScrapeWebsiteTool` | Evidence checks only. Same scrape refusal. Does not invent must-haves. |
| `communicator` | Candidate Outreach Strategist | Draft outreach templates for the top scored candidates | `SerperDevTool`, `ScrapeWebsiteTool` | Optional public tone lookup only. **No send-mail tool.** Templates are drafts with placeholders for recruiter name and company. |
| `reporter` | Candidate Reporting Specialist | Compile the recruiter-facing markdown report | none | `Task.context` = research + match + outreach. |

Memory / session: none. Each kickoff is stateless aside from the in-memory run record. Do not set `CREWAI_STORAGE_DIR` for product runs (`memory=False`).

Tool policy:

- Validate that YAML tool names resolve before `kickoff`. Unbound tools → Diagnostic, no kickoff (AC-013).
- Scrape wrapper: allow `http`/`https` public pages; deny hosts `linkedin.com` and `www.linkedin.com`; do not attach cookies or Authorization headers.
- Search snippets may still cite a LinkedIn URL as `source_url` when Serper returns one. That citation is a search hit, not a scraped profile. Contact fields stay unknown unless present on an allowed public page.
- Missing contact → `unverified` / contact unknown. Never invent email or phone (AC-003).

**Scoring rubric** (PRD Assumption: SAD-owned). Scores are recommendations for human review, not decisions.

| Factor | Points | Rule |
|--------|--------|------|
| Skills match | 0–40 | Overlap with written must-haves vs preferred qualifications only |
| Seniority fit | 0–20 | Compare to stated seniority. If seniority was omitted under “run anyway”, award 0 and label “not assessed” — do not infer a level |
| Evidence quality | 0–25 | Public `source_url` and evidence summary. `unverified` rows cap this factor at 5 |
| Location / remote fit | 0–15 | Compare to stated location or remote constraint. If omitted under “run anyway”, award 0 and label “not assessed” |
| **Total** | **0–100** | Sum of the four factors |

Protected-class attributes are not features: no photos, no inferred ethnicity, age, gender, or emotion/personality (P0-4, P2 prohibition). Vague phrases are not must-haves (see gate).

**Task / Turn Orchestration**:

| Order | Task id | Agent | Context | Expected output |
|-------|---------|-------|---------|-----------------|
| 1 | `research_candidates` | `researcher` | none (inputs: `job_requirements`, `assumptions`, `candidate_limit`) | Markdown list of up to N leads: name or public handle, evidence summary, `source_url` or `unverified`, contact unknown when absent. No code fences. |
| 2 | `match_and_score` | `matcher` | `research_candidates` | Ranked list: score per rubric, factor breakdown, justification citing only the requisition and Assumptions. |
| 3 | `draft_outreach` | `communicator` | `research_candidates`, `match_and_score` | Draft templates for the top candidates. Each template states it was **not sent**. Placeholders for recruiter name and company. |
| 4 | `compile_report` | `reporter` | `research_candidates`, `match_and_score`, `draft_outreach` | Single markdown report **without** wrapping code fences. |

Report headings required in `expected_output` for `compile_report`:

1. `## Job requirements`
2. `## Assumptions` (always present; “None” when the gate found no confirmed gaps)
3. `## Candidate profiles`
4. `## Ranked scores and justifications`
5. `## Outreach drafts`
6. `## Sources`
7. `## Recommendations for recruiter review`

`Task.guardrail` on `compile_report`: required headings present; body does not start with a code fence; contains the phrase that drafts were not sent; on failure, retry then Diagnostic (do not silently rewrite).

Error handling:

- `max_retry_limit=2` on each task.
- `max_iter=12` on each agent.
- Missing the selected LLM key (`OPENAI_API_KEY` when `LLM_PROVIDER=openai`, `XAI_API_KEY` when `LLM_PROVIDER=grok`) or `SERPER_API_KEY` → fail closed before kickoff, code `MISSING_API_KEY` (NFR-011). `GROK_API_KEY` is an alias for `XAI_API_KEY`. An unknown `LLM_PROVIDER` → `503` `CREW_FAILURE`.
- Tool/LLM/guardrail failure → run status `failed` or `partial`. Partial prior task text may be returned only with `partial: true`. No silent fill (AC-008).
- Cancellation: client disconnect does not kill the in-process crew in MVP (one active run). Operator restarts the process to cancel. Document this limit; queueing is deferred (NFR-013).
- Timeout: see budgets below. On breach, status `failed`, error code `TIMEOUT`, Diagnostic naming the last task id.

Performance budgets:

| Control | Value | Where |
|---------|-------|-------|
| `max_iter` | 12 | each agent |
| `max_retry_limit` | 2 | each task |
| `max_rpm` | 20 | crew |
| `max_execution_time` | 150 seconds | each agent |
| Kickoff wall clock | 480 seconds | API supervisor around `kickoff` |
| `temperature` | 0.2 | crew LLM |
| `max_tokens` | 8192 | crew LLM completion cap |
| Model | `LLM_PROVIDER=openai` uses `OPENAI_MODEL` (default `gpt-4o`). `LLM_PROVIDER=grok` uses `GROK_MODEL` (default `grok-4.7`) | env |
| `memory` | false | crew |
| Candidate N | default 10, min 5, max 10 | request or `CANDIDATE_LIMIT` |

Function-calling tool mode is fixed for the run. Do not switch mode mid-kickoff.

**Clarify-before-kickoff gate** (deterministic, API layer, before `crew.kickoff()`):

Input normalizes to `job_requirements`:

- `title` (required)
- `description`
- `responsibilities`
- `requirements` (must-haves)
- `preferred_qualifications` (optional)
- `location` (optional string)
- `remote` (optional: `onsite` | `hybrid` | `remote`)
- `perks_and_benefits` (optional)

Accept either a JSON object or a YAML/markdown blob with those keys. Chat may paste the blob or submit the form; both become this object. Serialized payload maximum **12 000** characters. `title` maximum 200 characters. Each text field maximum 4 000 characters. Over-cap → `422 VALIDATION`.

Hard block (no kickoff, `confirm_run_anyway` ignored):

- `title` missing, whitespace-only, or fewer than 2 characters after trim.
- Must-haves empty after the vague-phrase strip below.

Vague-phrase strip (case-insensitive) removes these phrases from `requirements` before the emptiness check:

`good culture fit`, `culture fit`, `team player`, `rockstar`, `ninja`, `fast learner`, `self-starter`, `self starter`, `passionate`, `passion`, `go-getter`, `go getter`, `wear many hats`, `hit the ground running`, `work hard play hard`.

After strip, if fewer than **3** alphanumeric tokens remain that are not English stopwords (`a`, `an`, `the`, `and`, `or`, `of`, `to`, `for`, `with`, `in`, `on`, `a`, `be`), treat must-haves as empty.

Clarify (no kickoff until the recruiter adds detail **or** sends an allowed confirmation):

- Seniority missing when must-haves are non-empty. Seniority is present if the combined title, description, responsibilities, and requirements match (case-insensitive) one of: `intern`, `junior`, `jr`, `mid-level`, `mid level`, `senior`, `sr`, `staff`, `principal`, `lead`, `manager`, `director`, `vp`, `executive`, `entry-level`, `entry level`, or the pattern `\b\d+\+?\s*years?\b`.
- Location/remote missing when `location` is empty **and** `remote` is empty **and** the same combined text lacks `remote`, `hybrid`, `onsite`, `on-site`, `work from home`, `wfh`.

“Run anyway” is allowed only for missing seniority and/or missing location/remote. Confirmation is the boolean `confirm_run_anyway: true` on a resubmit of the **same** normalized payload, or a chat reply whose trimmed text equals `run anyway` (case-insensitive). A bare `yes` is not confirmation.

When kickoff proceeds under confirmation, the API injects an `assumptions` list into the crew inputs, for example:

- `seniority unspecified; matcher must mark seniority fit as not assessed`
- `location unspecified; search the public web without a geography penalty`

The reporter must copy those lines into `## Assumptions` (AC-012).

**Runtime-Conditional Configuration** (Selected Runtime: `crewai`):

- Files: `config/agents.yaml`, `config/tasks.yaml`, entrypoint `crew.py` (or equivalent) that loads YAML and exposes one `kickoff(inputs)` function.
- Process type: sequential only.
- Task context chaining: as in the table above.
- `kickoff_for_each`: not used.
- Prompt Trace and task lifecycle logs for Build go under `project-context/2.build/logs` with secrets redacted. Product runtime logs to stdout with the same redaction.
- Do not include a LinkedIn tool in YAML.

Subsections for `claude-agent-sdk` and `cursor-sdk` are not applicable. Resolved runtime is `crewai`.

---

### 3. Frontend Architecture Specification

**Technology Stack** (from PRD or justified defaults):

| Concern | Choice |
|---------|--------|
| Framework | Vite + React 18 + TypeScript |
| UI library | None (semantic HTML, minimal CSS) |
| Styling | System theme via `color-scheme` and `prefers-color-scheme`; `visual_style: minimal`; `prefer_modals: false` |
| Type safety | TypeScript strict (`coding_standards.type_checking: true`) |
| State | Component state plus one small run-status module. No global store library. |
| File size | Prefer files under 400 lines (`max_file_lines`) |

**Application Structure**:

- Single route `/` (chat). No other product routes in MVP.
- Suggested layout (frontend epic owns the files; names are guidance):
  - `src/App.tsx` — page shell
  - `src/components/ChatTranscript.tsx` — messages
  - `src/components/Composer.tsx` — paste/form and send
  - `src/components/RunStatus.tsx` — task label and errors
  - `src/api/client.ts` — **stubs only during the frontend epic**; integration epic binds the real base URL
- API client boundary: the frontend epic renders against typed request/response shapes from §4 and fixture JSON. It does not import the Python crew.
- Responsive: desktop-first; readable below 768px; not a native app.
- Accessibility MVP (NFR-015, NFR-016): composer and send usable from the keyboard; visible focus; error text associated with the composer; contrast sufficient to read errors. Full WCAG AA audit is stretch, not a release blocker.

**Interface Requirements**:

- Primary surface: chat transcript, composer (paste YAML/markdown **or** fields for title, must-haves, description, responsibilities, preferred qualifications, location, remote, perks), send control.
- States: empty, needs-clarification, in-progress, error, completed (AC-010).
- Needs-clarification: list each gap and whether “run anyway” is allowed. Do not show a spinner as if the crew had started.
- In-progress: name the current task (`research_candidates`, `match_and_score`, `draft_outreach`, `compile_report`) from the poll payload. Acknowledge the user’s submit immediately in the transcript (NFR-002); do not wait for the report to paint the user message.
- Completed: assistant message is the report markdown (rendered as markdown, not inside a code block) plus copy and `.md` download.
- Error: show `error.message` for missing key, timeout, zero public hits, scrape blocked, guardrail/prerequisite Diagnostic. Offer retry or edit. Do not clear the requisition text.
- Copy on the page, always visible: recommendations require human review; the app does not reject or contact candidates.
- Future Work (ATS, send, SSO) is not shown. If a placeholder is added, label it “Future work”.

---

### 4. Backend Architecture Specification

**API Architecture**:

Base URL local: `http://127.0.0.1:8000`. JSON UTF-8. No token streaming.

`GET /health`

- Response `200`: `{"status":"ok"}`

`POST /api/runs`

Request:

```json
{
  "job_requirements": {
    "title": "string",
    "description": "string",
    "responsibilities": "string",
    "requirements": "string",
    "preferred_qualifications": "string or null",
    "location": "string or null",
    "remote": "onsite | hybrid | remote | null",
    "perks_and_benefits": "string or null"
  },
  "raw_blob": "string or null",
  "confirm_run_anyway": false,
  "candidate_limit": 10
}
```

`raw_blob`, when non-empty, is parsed as YAML into `job_requirements`. Explicit JSON fields override blob keys when both are sent.

Responses:

- `202` crew accepted: `{"run_id":"uuid","status":"queued","gaps":[]}`
- `200` needs clarification (no kickoff): `{"run_id":null,"status":"needs_clarification","gaps":[{"field":"seniority","reason":"string","run_anyway_allowed":true}]}`
- `422` hard block or schema error: error envelope, code `VALIDATION`
- `409` a crew is already active: code `CREW_BUSY`
- `503` missing API key at startup/request: code `MISSING_API_KEY`

`GET /api/runs/{run_id}`

- `200`:

```json
{
  "run_id": "uuid",
  "status": "queued | running | completed | failed | partial",
  "current_task": "research_candidates | match_and_score | draft_outreach | compile_report | null",
  "partial": false,
  "assumptions": ["string"],
  "report_markdown": "string or null",
  "error": null
}
```

- `404` unknown id.

Error envelope (all error statuses):

```json
{
  "error": {
    "code": "VALIDATION | MISSING_API_KEY | CREW_BUSY | TIMEOUT | CREW_FAILURE | GUARDRAIL",
    "message": "operator-safe string",
    "run_id": "uuid or null"
  }
}
```

Validation: Pydantic models matching the schema above. `candidate_limit` integer 5–10, default 10.

Rate limiting: at most **one** run in `queued` or `running`. Further `POST /api/runs` returns `409` until that run reaches `completed`, `failed`, or `partial`. No other rate limiter in MVP.

Alignment: the HTTP layer does not embed agent prompts; it calls the crew entrypoint with `job_requirements`, `assumptions`, and `candidate_limit`.

**Data Architecture** (MVP default: none unless PRD requires):

- No database and no ORM.
- Process memory: map `run_id → run record` (status, current task, assumptions, report, error). Lost on restart. That matches single-operator local use.
- Optional write of the completed markdown to `var/runs/{run_id}.md` (gitignored). This is the operator’s copy, not a candidate store. Last-N history (P1) is deferred; MVP keeps records only until process exit, and the UI holds the transcript for the browser session.

**Runtime Integration Layer**:

- FastAPI checks the selected LLM key (`OPENAI_API_KEY` or `XAI_API_KEY`) and `SERPER_API_KEY` on `POST /api/runs`. Missing key: process stays up so `/health` works, and the POST returns `503 MISSING_API_KEY`.
- `POST` that passes the gate assigns `run_id` (UUID4), stores `queued`, starts `kickoff` on a worker thread, and returns `202` without waiting for the crew.
- A task callback updates `current_task` and status `running`.
- Supervisor enforces the 480s wall clock and maps exceptions to `failed` / `partial` plus the error envelope.
- Logging: run id, task start/stop, retry count, error code, token usage and search-call counts when the runtime exposes them. Redact values of the env names in § Authentication. Prompt Trace for Build-phase runs is written under `project-context/2.build/logs`.
- Configuration of agents and tasks is YAML only, loaded at process start. Invalid YAML or unknown tools → startup Diagnostic in logs and `POST /api/runs` returns `503` code `CREW_FAILURE` with a message that the crew failed to load.

**Authentication & Secrets**:

Environment variable **names** only:

| Name | Required | Purpose |
|------|----------|---------|
| `LLM_PROVIDER` | no (default `openai`) | `openai` or `grok` for the whole process |
| `OPENAI_API_KEY` | when `LLM_PROVIDER=openai` | OpenAI LLM |
| `OPENAI_MODEL` | no (default `gpt-4o`) | OpenAI model id |
| `XAI_API_KEY` | when `LLM_PROVIDER=grok` | Grok API key from the xAI console. `GROK_API_KEY` is an accepted alias |
| `GROK_MODEL` | no (default `grok-4.7`) | Grok model id. Calls use base URL `https://api.x.ai/v1` |
| `SERPER_API_KEY` | yes | Web search |
| `AAMAD_TARGET_RUNTIME` | yes (`crewai`) | Adapter selection |
| `CREWAI_TELEMETRY_OPT_OUT` | no (recommend `true`) | Telemetry |
| `APP_NAME` | no | Log label |
| `APP_ENV` | no | `development` / `production` label |
| `CANDIDATE_LIMIT` | no (default `10`) | Default N when the request omits it |
| `HOST` | no (default `127.0.0.1`) | Bind address |
| `PORT` | no (default `8000`) | Bind port |

Do not add `LINKEDIN_COOKIE`. `.env.example` lists the names above with empty or non-secret placeholders. No secret values in this artifact.

---

### 5. DevOps & Deployment Architecture

**CI/CD** (minimal MVP):

- Stages: lint, test, build. No deploy job.
- Python: lint (Ruff or equivalent) and `pytest` for unit and integration tests mapped to AC ids.
- Frontend: TypeScript check, lint, Vite production build.
- Pipeline config is produced in Deliver. Do not trigger a live deploy from CI without explicit operator authorization.

**Hosting**:

- Smallest target: one local process. FastAPI serves `/api` and `/health` and, after the frontend build, the static `dist/` files.
- Alternative documented in the runbook: two dev processes (Vite dev server and Uvicorn) for Build.
- Container: optional single-service image in Deliver (CPU, no GPU). Compose is optional and still one app service. No multi-region, no IaC beyond that image/compose file.
- Port: `8000`. Health: `GET /health`.
- Memory: sized for one crew plus the Python process. No GPU.

**IaC / multi-region / advanced monitoring**: Future Work.

**Observability**:

- Baseline: stdout logs (run id, task, error code, token/search counts) and `/health`.
- Advanced APM, tracing vendors, and uptime SLAs: deferred (NFR-004 best-effort).

---

### 6. Data Flow & Integration Architecture

Request path:

1. Recruiter submits from the chat composer.
2. Frontend `POST /api/runs` (integration epic).
3. API parses and runs the clarify gate.
4. On hard block or clarification, the UI shows gaps or validation errors and **does not** start the crew.
5. On accept, API returns `run_id` immediately; a worker calls `crew.kickoff`.
6. Frontend polls `GET /api/runs/{run_id}` about every 2 seconds until a terminal status.
7. Terminal `completed`: transcript shows `report_markdown`. Terminal `failed` or `partial`: transcript shows the error and any labeled partial text.

External integrations (MVP only):

| System | Direction | MVP rule |
|--------|-----------|----------|
| OpenAI chat completions | outbound HTTPS | `LLM_PROVIDER=openai`, `OPENAI_API_KEY`, model from `OPENAI_MODEL` |
| xAI chat completions (Grok) | outbound HTTPS | `LLM_PROVIDER=grok`, `XAI_API_KEY`, model from `GROK_MODEL`, base URL `https://api.x.ai/v1` |
| Serper search API | outbound HTTPS | `SERPER_API_KEY` |
| Public websites | outbound HTTPS GET via scrape tool | Allowed pages only; LinkedIn host denied |
| LinkedIn authenticated APIs | — | Forbidden |
| Email / ATS | — | Forbidden / out of scope |

Error propagation: crew exceptions become the error envelope. The UI displays `message` and keeps the composer contents. Secrets never appear in `message`, the report, or logs.

---

### 7. Performance & Scalability Specifications

| ID | MVP target | Mechanism |
|----|------------|-----------|
| NFR-001 | P95 kickoff ≤ 8 minutes for N≤10 | 480s supervisor; then `TIMEOUT` Diagnostic |
| NFR-002 | Submit acknowledged ≤ 2 seconds | `202` before `kickoff` returns; UI paints the user message on submit |
| NFR-003 | 1 active crew per process | `409 CREW_BUSY` |
| NFR-004 | Best-effort local/dev | No availability SLA |

Scaling path: deferred. Bottleneck is LLM and search RPM, not HTTP. `max_rpm=20` is the cost control. Raising concurrency, adding a queue, or multi-tenant hosting waits on a later PRD change (NFR-013).

Token / cost controls: crew `max_rpm`, `max_iter`, `max_tokens=8192`, N capped at 10, temperature 0.2. Operator can set `candidate_limit` to 5 on a request to cut search and token use.

---

### 8. Security & Compliance Architecture

- **AuthN/AuthZ:** none inside the app. Trust boundary is the loopback interface. `HOST` default `127.0.0.1`. No SSO, no RBAC (Future Work).
- **Secrets:** env vars only; redact in traces; `forbid_committed_secrets` from the example config applies.
- **Input validation:** schema limits in §4; gate in §2; scrape host denylist.
- **Encryption:** TLS is the provider’s (OpenAI, Serper, public sites). Local HTTP on loopback is acceptable for MVP. Do not log request bodies that may contain unnecessary personal data beyond the job requisition.
- **PII:** candidate names and public URLs exist only in the run record, the chat transcript, and an optional `var/runs` export. No shared database (NFR-007).
- **Employment decisions:** recommend-only copy in UI and report (NFR-006). No solely automated reject/advance.
- **Dependency audit:** required on the Build/Deliver path (NFR-009, example config).
- **Security assessment:** required before Deliver because example config sets `security.require_security_assessment: true` and no project `aamad.config.yml` overrides it (NFR-008).
- **Compliance packs** (NYC AEDT, EU AI Act conformity evidence): Future Work. Open Question remains on whether the UI shows a jurisdiction banner.

---

### 9. Testing & Quality Assurance Specifications

Map tests to acceptance criteria (`testing.map_to_acceptance_criteria: true`). Unit and integration tests are required.

| Layer | What to prove |
|-------|----------------|
| Unit | Gate: empty title, empty must-haves, vague-only strip, missing seniority, missing location, “run anyway” allowed vs ignored, payload length, N bounds. Rubric weights sum to 100. Report guardrail heading check with fixture markdown. |
| Integration | API: `202` + poll to `completed` with **mocked** LLM and search; `needs_clarification` does not call `kickoff`; `503` when keys missing; `409` when a run is active; report task receives three context fixtures (AC-002). |
| Smoke | One happy-path UI session against mocks or a recorded fixture: submit → in-progress task label → report with sources and “not sent”. One clarification session. One error session (timeout or missing key). |
| Runtime | YAML loads four agents and four tasks; forbidden tool names (`LinkedIn`, cookie) absent; `memory` false; sequential process. |
| Security | `@security.eng` before Deliver. Checklist includes no `LINKEDIN_COOKIE`, no send tool, secrets absent from traces. |
| KPI hours saved | Not a CI assertion (PRD §7). QA may check that the metric definition exists for the operator diary. |

Crew tests should stub network. Live Serper/OpenAI calls are optional manual checks, not the default CI path.

---

### 10. MVP Launch & Feedback Strategy

Commercial launch and GTM are **N/A** (PRD §9). The launch is a local/demo MVP for one operator.

Pilot criteria:

- QA happy path passes with mocked tools.
- A real requisition run (operator machine, real keys) returns at least one URL-backed lead or an explicit empty/partial Diagnostic — never invented contacts.
- UI states human review and that outreach was not sent.
- Security assessment recorded when Deliver starts.

Success metrics (from PRD §7, not re-scoped here):

- ≥ 3 hours/week and ≥ 2 hours/req on first-pass sourcing, scoring, and outreach drafting, measured by operator diary after use.
- Time-to-shortlist under 8 minutes typical.
- Zero auto-contact incidents; zero LinkedIn cookie usage.
- 100% of non-unverified candidate rows have `source_url`.

After the first usable demo, iteration priority is: sourcing quality and hallucination fixes, then P1 progress streaming and local report history. ATS and send stay out until a new PRD scope.

---

## Implementation Guidance for AI Development Agents

1. Foundation setup per `setup.md` epic — `@project.mgr`: Python env, CrewAI, FastAPI, Vite app skeleton, `.env.example` names from §4, `var/runs/` gitignored, `AAMAD_TARGET_RUNTIME=crewai`.
2. Frontend MVP UI without backend wiring — `@frontend.eng`: states in §3 against fixtures.
3. Backend runtime scaffolding per adapter rule — `@backend.eng`: YAML crew, gate, FastAPI, mocked-testable kickoff.
4. Integration epic wires FE ↔ BE — `@integration.eng`: base URL, poll loop, error envelope.
5. QA validates unit, integration, and smoke paths — `@qa.eng`.
6. Security assessment — `@security.eng` — then Deliver packages deploy/CI/runbook/user guide only. No live deploy without operator authorization.

Build personas halt with Diagnostic on missing prerequisites, unbound tools, or heading mismatches. They do not invent requirements when this SAD and the PRD are silent; they record Assumptions and Open Questions.

---

## Architecture Validation Checklist

- [x] PRD requirements mapped to architectural components
- [x] Agents designed for the domain and selected runtime
- [x] Frontend and backend contracts agree on schemas / streaming (poll + final markdown; no token stream)
- [x] Secrets via env vars only
- [x] MVP vs Future Work boundaries explicit
- [x] Resolved `AAMAD_TARGET_RUNTIME` recorded in Audit

### Traceability (PRD → architecture)

| PRD id | Architectural home |
|--------|---------------------|
| P0-1 / AC-001 | §4 `POST /api/runs`; §2 gate title rule |
| P0-2 / AC-002 | §2 task table and context |
| P0-3 / AC-003 | §2 researcher output; scrape denylist |
| P0-4 / AC-004 | §2 rubric |
| P0-5 / AC-005 | §2 communicator; no send tool |
| P0-6 / AC-006 | §2 report headings; §3 download |
| P0-7 / AC-007 | §3 recommend-only copy; no decision API |
| P0-8 / AC-008 | §4 statuses `failed`/`partial`; §6 |
| P0-9 / AC-009 | §4 secret names |
| P0-10 / AC-010 | §3 states |
| P0-11 / AC-011–AC-013 | §2 gate; Diagnostic halt |
| NFR-001–004 | §7 |
| NFR-005–010 | §8 |
| NFR-011–014 | §2, §4, §7 |

---

## Sources

- `project-context/1.define/prd.md` (product-mgr, create-prd, 2026-10-16).
- `project-context/1.define/mrd.md` (product-mgr, create-mrd, 2026-10-13) — sequential four-agent feasibility, ToS constraint, local deployment.
- `project-context/1.define/context-summary.md`.
- `.cursor/templates/sad-template.md`.
- `.cursor/agents/system-arch.md`.
- `.cursor/rules/adapter-crewai.mdc`, `.cursor/rules/adapter-registry.mdc`, `.cursor/rules/aamad-core.mdc`.
- `aamad.config.example.yml` (no project `aamad.config.yml`).
- `.env.example` (variable names only; model default `gpt-4o`).
- Operator request: `@system.arch` create SAD, confirm `AAMAD_TARGET_RUNTIME=crewai`, 2026-10-19.

## Assumptions

- No `aamad.config.yml`; example config preferences apply (system theme, minimal UI, type checking, max 400 lines, security assessment required, unit and integration tests required, user guide required).
- No user-story files; PRD acceptance criteria are the trace anchors.
- Shell environment in this session did not export `AAMAD_TARGET_RUNTIME`. Resolution is `crewai` because `.env` and `.env.example` set `AAMAD_TARGET_RUNTIME=crewai`, example config `runtime.target` is `crewai`, and the PRD selects `crewai`. Adapter registry default would also be `crewai`.
- Operator message named “Researcher, Evaluator, Recommender”. Those map onto the PRD quartet as recorded in AD-02; the SAD does not drop `communicator` or `reporter`.
- “Run anyway” confirmation is `confirm_run_anyway: true` or the exact reply `run anyway`, not a free-form yes (closes PRD Open Question 10 for MVP).
- Default model `gpt-4o` and temperature `0.2` close PRD Open Question 1 for the OpenAI provider. Operator request on 2026-10-21 adds `LLM_PROVIDER=grok`, which calls xAI with `XAI_API_KEY` and default model `grok-4.7`. One provider is selected for the process. A cheaper OpenAI model remains an `OPENAI_MODEL` change, not a second code path.
- Default N stays **10** (PRD). Request may set 5–10.
- Polling every ~2 seconds is sufficient for task progress. Token streaming stays P1.
- Vague-phrase list and the “3 remaining tokens” rule are the MVP heuristic for AC-011. They will miss novel fluff and should be extended by QA fixtures, not by an extra LLM call.
- Seniority lexicon and location lexicon are English-only, matching the PRD language constraint.
- `max_rpm=20` and 150s per agent are compatible with an 8-minute outer cap for typical N=10 runs. If real runs exceed 480s, the operator lowers N; do not raise the cap without editing this SAD.
- Loopback bind is enough for the local demo. Basic auth is not added.
- Hours-saved diary stays outside the app (spreadsheet). In-app capture is not MVP.

## Open Questions

1. Should `@project.mgr` copy `aamad.config.example.yml` to `aamad.config.yml` before Build? (PRD Open Question 3.)
2. Is any people-data API besides Serper and public pages in scope? Current answer from PRD: no. Reconfirm before Build if the operator has a licensed source. (PRD Open Question 4.)
3. Jurisdiction banner (US vs EU) in the chat footer? Not designed here. (PRD Open Question 8.)
4. If live runs regularly time out at N=10, should the default N change to 5? Left as an operator request flag until measured.
5. `.env.example` is missing `SERPER_API_KEY` (and the optional names in §4). Setup should add placeholders. Confirm the operator’s search vendor is Serper before locking the tool class.
6. Hours/week diary format (spreadsheet vs later in-app prompt) remains the operator’s choice. (PRD Open Question 11.)
7. If the operator runs fewer than one requisition per week, the binding KPI is ≥ 2 hours/req. (PRD Open Question 12.) Product behavior does not change.

## Audit

- **timestamp:** 2026-10-19T18:50:00Z
- **persona id:** `system-arch`
- **action:** `create-sad`
- resolved AAMAD_TARGET_RUNTIME: `crewai`
- **llm / temperature / max_tokens (product runtime, specified for Build):** provider from `LLM_PROVIDER` (`openai` default, or `grok`); OpenAI model `gpt-4o` via `OPENAI_MODEL`; Grok model `grok-4.7` via `GROK_MODEL` at `https://api.x.ai/v1`; temperature `0.2`; `max_tokens` `8192`; `max_rpm` `20`; `max_iter` `12`; `max_retry_limit` `2`; agent `max_execution_time` 150s; kickoff wall clock 480s; `memory=False`; function-calling tool mode fixed for the run
- **revision:** 2026-10-21 — operator request: configurable OpenAI or Grok key. Persona `backend-eng`.
- **Prompt Trace:** omitted — this artifact is an architecture specification derived from PRD/MRD/template, not a crew kickoff
- **tools:** read PRD, MRD, context summary, SAD template, system-arch persona, `aamad.config.example.yml`, `.env.example`; confirmed `AAMAD_TARGET_RUNTIME` in `.env` / `.env.example`
- **outputs:** `project-context/1.define/sad.md`

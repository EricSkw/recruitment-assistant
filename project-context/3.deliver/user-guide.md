# User Guide — Recruitment Assistant

Release **0.1.0**. Local chat for one recruiter. Runtime is CrewAI.

### 1. Product Overview

Recruitment Assistant takes a professional or technical requisition and returns one markdown report. A sequential crew researches public leads, scores them against the requisition, drafts outreach text, and compiles the report in the chat. You decide who to contact and what to send. The app does not reject, advance, or message anyone.

It is for one recruiter or hiring manager on one machine. A hiring manager can read the report. It is not an ATS, a job board, or a LinkedIn Recruiter replacement. There is no login.

MVP limits recorded in `project-context/2.build/qa.md` (2026-10-24) and `project-context/3.deliver/deploy.md`:

- QA showed a completed report in the browser against a mock of the run API. That pass did not include a live provider and Serper kickoff. AC-003, AC-004, AC-005, and AC-012 were not proven on a live crew. AC-009 is **Fail** in `qa.md` because `.env.example` then held a non-placeholder `XAI_API_KEY`. The Deliver read of `.env.example` shows placeholder text only. Rotate any key that was in that file. That observation is not a new QA pass.
- A later report file is at `project-context/3.deliver/execution-results.md`. This guide does not treat that file as a closed QA gap.
- Recommendations require human review. Drafts are not sent.
- Run state lives in the API process. A restart drops it. Completed reports may also be written under `var/runs/`.
- Keep the app on localhost. `security.md` was not written.

### 2. Prerequisites

- Linux or WSL. Python 3.12 (CrewAI accepts `>=3.10` and `<3.14`). Node.js 18 for the local UI. QA used Linux Node v18.19.1. Use the Linux Node inside WSL. A Windows `npm` cannot install into this WSL project path.
- Docker Compose v2 only for the container path. This environment did not have Docker integrated. The image was not built here.
- A desktop browser that can open `http://127.0.0.1:5173/` (local UI) or `http://127.0.0.1:8000/` (container UI).
- Accounts for the selected model provider and for Serper. Set the values in an untracked `.env`. Names only:

| Name | When it is required |
|------|---------------------|
| `LLM_PROVIDER` | Optional. Default `openai`. Also `grok` or `openrouter` |
| `OPENAI_API_KEY` | `LLM_PROVIDER=openai` |
| `XAI_API_KEY` | `LLM_PROVIDER=grok`. `GROK_API_KEY` is an alias |
| `OPENROUTER_API_KEY` | `LLM_PROVIDER=openrouter` |
| `SERPER_API_KEY` | Required to start a crew. `/health` still works if it is empty |

Optional names are in `.env.example`: `OPENAI_MODEL`, `GROK_MODEL`, `OPENROUTER_MODEL`, `AAMAD_TARGET_RUNTIME`, `CREWAI_TELEMETRY_OPT_OUT`, `CREWAI_TRACING_ENABLED`, `LOG_LEVEL`, `APP_NAME`, `APP_ENV`, `CANDIDATE_LIMIT`, `HOST`, `PORT`. Do not add `LINKEDIN_COOKIE`.

### 3. Installation

Local install from the repo root (`project-context/3.deliver/deploy.md`). `project-context/2.build/setup.md` records the same toolchains. Its start command runs `main.py` from `src/backend`. The repo-root `python main.py` is the path below.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
cd src/frontend && npm ci
```

`requirements.txt` matches the pins in `src/backend/requirements.txt`. Edit `.env` with your own values. The tracked example file should contain placeholders, not real keys. There is no project `aamad.config.yml`. Example preferences live in `aamad.config.example.yml`. Runtime target in `.env.example` is `crewai`. Leave `VITE_API_BASE` unset so the dev server proxies `/api` and `/health`.

Restart the API after any `.env` change. The process does not reload the file.

Start the API from the repo root:

```bash
source .venv/bin/activate
python main.py
```

That listens on `http://127.0.0.1:8000` (`HOST` / `PORT`). It does not serve the chat page. Start the chat page in a second terminal:

```bash
cd src/frontend && npm run dev
```

Smoke check:

```bash
curl -sS http://127.0.0.1:8000/health
curl -sS http://127.0.0.1:5173/health
```

Expect `{"status":"ok"}` from both. Open `http://127.0.0.1:5173/`.

Container install, start, and health check are in `project-context/3.deliver/deploy.md`. The container serves the built page on port 8000. It does not use the Vite server. `PORT` inside the container stays 8000. Compose publishes `127.0.0.1:8000` only.

Stop local processes with Ctrl+C in each terminal. An in-flight kickoff stops with the API process.

### 4. Getting Started

1. Open `http://127.0.0.1:5173/` for local dev, or `http://127.0.0.1:8000/` if the container is running.
2. Read the banner: “Recommendations require human review. This app does not reject or contact candidates.”
3. Status starts at “No run yet.” Use **Fields**, or **Paste YAML**. **Fill example requisition** loads a sample senior backend role: title “Senior Backend Engineer”, must-haves “Python, FastAPI, PostgreSQL”, location Lisbon, remote Hybrid, candidate count 10.
4. On **Fields**, set title and must-have skills. Set candidate count from 5 to 10. Add location and remote (onsite, hybrid, or remote) when you know them. Description, responsibilities, preferred qualifications, and perks are optional. On **Paste YAML**, the API parses the blob. A placeholder in the box shows `title`, `requirements`, `location`, and `remote`.
5. Press **Send** (or Ctrl+Enter / Cmd+Enter). Your line appears in the transcript before the report exists.
6. If the gate needs more detail, the page says “The crew was not started.” and “Needs clarification. The crew has not started.” It lists each gap. The form text stays. Add the missing pieces, or press **Run anyway** when every listed gap says that is allowed. Empty title and empty or vague-only must-haves cannot use run anyway.
7. When a run is accepted, status moves through `research_candidates` (Researcher), `match_and_score` (Evaluator), `draft_outreach` (Recommender), and `compile_report` (Recommender). Before the first task finishes it can read “Queued. The crew has not finished a task yet.” The page polls about every 2 seconds. Responses are not streamed.
8. On completion, status reads “Completed.” The transcript shows the report as markdown: job requirements, assumptions when the run continued with confirmed gaps, profiles, scores, outreach drafts, sources, and recommendations. Use **Copy** or **Download .md**. QA could not confirm clipboard or the file save in the automation browser. Retry those in your own browser. A partial result reads “Partial result. Review the labeled text before using it.”

Screenshots are not included.

A CLI test entry uses the same gate and crew and does not start the HTTP server. Flags, exit codes, and sample commands are in `project-context/3.deliver/deploy.md` under CLI (testing). A command that reaches the crew calls the configured LLM and Serper.

### 5. Everyday Use

| Task | What you should see |
|------|---------------------|
| Empty title or empty must-haves | `422` `VALIDATION`. Retry and Edit requisition stay available. The crew does not start |
| Missing seniority or location | `needs_clarification`. Status says the crew has not started. `run_id` is null |
| Vague must-have only (for example “good culture fit”) | `VALIDATION` after the vague phrase is removed, including when run anyway is set |
| Second send while a crew is running | `409` `CREW_BUSY`. Wait, or restart the API to abandon the run |
| Completed report | Ranked leads with a source URL or an unverified mark. Outreach text states it was not sent |
| Provider or Serper key missing | `503` `MISSING_API_KEY`. The gap list is not shown. Fix `.env` and restart the API |
| Unknown or expired run | `404` with message `Unknown run id.` |
| API unreachable | The page shows `CREW_FAILURE` with an operator-safe message |

Scores and drafts are input for your review. They are not a hiring decision. A missing email or phone stays unverified. The crew does not invent a must-have and treat it as decided.

Candidate count on the form overrides the `CANDIDATE_LIMIT` default for that request. The allowed range is 5–10. One crew runs at a time in the process. Closing the browser does not cancel a kickoff.

### 6. Troubleshooting

| Problem | What to try |
|---------|-------------|
| Page loads, status never moves | Confirm the API process is the one you started after the last `.env` edit. Local UI is port 5173 and the API is port 8000. The container UI is port 8000 and does not use Vite |
| `MISSING_API_KEY` | Set the key for `LLM_PROVIDER` and set `SERPER_API_KEY`. Restart |
| Run disappears after a restart | Expected. Memory is process-local. Submit again. Older ids return `Unknown run id.` Copies already written under `var/runs/` stay on disk |
| Browser closed mid-run | The kickoff continues until it finishes, times out, or you stop the API |
| Copy failed | The button reports “Copy failed. Use download.” Use **Download .md**. QA saw the clipboard failure in the automation browser |
| Warning about function callbacks | CrewAI serialization notice. `/health` can still be ok. The startup line should include `crew_load=ok` |
| Timeout | The run stops at the supervisor limit (480 seconds) and names the last task |
| `docker` command missing | Use the two local processes. See deploy.md |
| No “View traces” link | Tracing is off, the API was not restarted after `.env` changed, or `crewai login` has not been run |

Logs: the API process stdout and `logs/trace.log` (logger `recruitment`, level `LOG_LEVEL`, default INFO). `/health` is recorded only at DEBUG. Secret values are redacted when they appear in those lines. Request bodies are not written there. Optional reports stay in `var/runs/`. `logs/prompt-trace.md` holds agent and task templates, not kickoff inputs. In Docker, use `docker compose logs`. The container copy of `logs/` goes away with the container. `var/runs` is mounted from the host.

The Application Crew runs with CrewAI `tracing=True` unless `CREWAI_TRACING_ENABLED` is `false`, `0`, `no`, or `off`. A traced kickoff can send requisition and candidate text to CrewAI AMP. On a shared machine, set that variable to `false` and restart. Dashboard links need `crewai login` from the repo root with the virtualenv active. `CREWAI_TELEMETRY_OPT_OUT=true` is separate and should stay on. Full operator detail is in deploy.md.

### 7. Deployment Notes (operators)

The runbook is `project-context/3.deliver/deploy.md`. It covers the env matrix, loopback binding, compose, CI, monitoring, and rollback. CI lints, tests, and builds. It does not deploy.

Rollback, short form: stop the processes or `docker compose down`, check out the previous revision, reinstall if `requirements.txt` or `src/frontend/package-lock.json` changed, start again. In-memory runs are not restored. Files already saved under `var/runs/` stay on disk. Nothing in this guide performs a remote deploy.

Keep the published port on `127.0.0.1`. Browser CORS allows `http://127.0.0.1:5173` and `http://localhost:5173`. The container page is same-origin.

## Sources

- `project-context/1.define/prd.md`
- `project-context/1.define/sad.md` (DevOps and Deployment Architecture, environment names)
- `project-context/2.build/setup.md`
- `project-context/2.build/integration.md`
- `project-context/2.build/qa.md`
- `project-context/2.build/frontend.md` (example requisition and chat labels; the wired client is `integration.md`)
- `project-context/2.build/backend.md`
- `project-context/3.deliver/deploy.md`
- `.cursor/templates/user-guide-template.md`
- `.env.example` (names and placeholders only)
- `aamad.config.example.yml` (`documentation.require_user_guide: true`). No project `aamad.config.yml`
- `security.md` is not in the repo

## Assumptions

- Local URLs and the repo-root `python main.py` plus Vite match deploy.md. `setup.md` and `integration.md` also document starting `main.py` from `src/backend`.
- The sample requisition button matches `exampleDraft()` in `src/frontend/src/draft.ts`.
- Docker steps are documented for later use. They were not executed while writing this guide.
- QA’s scoped gaps remain the verification record. Placeholder text now in `.env.example` does not reopen AC-009.
- No model call was made while writing this guide. Prompt Trace omitted for that reason.

## Open Questions

1. Clipboard and `.md` download still need a confirmation in the operator’s browser (QA AC-006).
2. `qa.md` still records the first live crew run as outstanding. Who updates that record after a requisition with a real provider key and `SERPER_API_KEY`?
3. Security assessment is not written. Who runs `@security.eng` before any host that is not this operator’s loopback?
4. Who runs `crewai login` before the first traced kickoff so the dashboard link resolves?

## Audit

- **timestamp:** 2026-10-25T16:11:22Z
- **persona id:** `devops-eng`
- **action:** `document-user-guide`
- **resolved AAMAD_TARGET_RUNTIME:** `crewai`
- **llm / temperature / max_tokens:** none. No model call. Prompt Trace omitted for that reason

## Audit

- **timestamp:** 2026-10-25T18:54:19Z
- **persona id:** `devops-eng`
- **action:** `document-user-guide` (log locations and tracing pointer)
- **resolved AAMAD_TARGET_RUNTIME:** `crewai`
- **llm / temperature / max_tokens:** none. No model call. Prompt Trace omitted for that reason

## Audit

- **timestamp:** 2026-10-25T23:55:36Z
- **persona id:** `devops-eng`
- **action:** `document-user-guide`
- **resolved AAMAD_TARGET_RUNTIME:** `crewai` (`.env.example`, PRD, SAD, deploy.md; shell export was not required)
- **llm / temperature / max_tokens:** none. No model call. Prompt Trace omitted for that reason
- **tools:** read devops persona, user-guide template, prd.md, sad references, setup.md, integration.md, qa.md, deploy.md, `.env.example`, `aamad.config.example.yml`, frontend composer and draft labels
- **outputs:** `project-context/3.deliver/user-guide.md`

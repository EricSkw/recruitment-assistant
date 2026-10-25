# User Guide — Recruitment Assistant

## 1. Product Overview

Recruitment Assistant is a local chat tool for a first pass on a professional or technical requisition. You paste or type the role. A sequential CrewAI crew researches public leads, scores them, drafts outreach text, and returns one markdown report in the chat. You decide who to contact and what to send.

It is for one recruiter or hiring manager on one machine. It is not an ATS, not a job board, and not a LinkedIn Recruiter replacement.

MVP limits from QA (2026-10-24):

- A completed report was shown in the browser only against a mock of the run API. A live provider and Serper kickoff was not part of that pass.
- Recommendations require human review. The app does not reject, advance, or message candidates.
- Run state lives in the API process. A restart drops it.
- There is no login. Keep the app on localhost.
- `security.md` was not written. Treat that as an open control for this Tier-0 package.

## 2. Prerequisites

- Linux or WSL, Python 3.12, Node.js 18 for the local UI.
- Docker Compose v2 only if you use the container path. This environment did not have Docker integrated.
- A browser that can open `http://127.0.0.1:5173/` (local) or `http://127.0.0.1:8000/` (container).
- API key environment variables (names only): `OPENAI_API_KEY` when `LLM_PROVIDER=openai`, `XAI_API_KEY` when `LLM_PROVIDER=grok`, or `OPENROUTER_API_KEY` when `LLM_PROVIDER=openrouter`. `SERPER_API_KEY` is required to start a crew. `GROK_API_KEY` is an alias of `XAI_API_KEY`. No `LINKEDIN_COOKIE`.

## 3. Installation

Local, from the repo root:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
cd src/frontend && npm ci
```

Edit `.env` with your own values. The tracked example file should contain placeholders, not real keys. There is no project `aamad.config.yml`. Runtime target in `.env.example` is `crewai`.

Start the API from the repo root:

```bash
source .venv/bin/activate
python main.py
```

Start the chat page in a second terminal:

```bash
cd src/frontend && npm run dev
```

Smoke check:

```bash
curl -sS http://127.0.0.1:8000/health
```

Expect `{"status":"ok"}`. The same check through the dev server is `http://127.0.0.1:5173/health`.

Container install, start, and health check are in `project-context/3.deliver/deploy.md`. The container serves the built page on port 8000. It does not use the Vite server.

## 4. Getting Started

1. Open `http://127.0.0.1:5173/` for local dev, or `http://127.0.0.1:8000/` if the container is running.
2. Read the banner. Recommendations need a person. Drafts are not sent.
3. Use **Fields**, or **Paste YAML**. **Fill example requisition** loads a sample senior backend role.
4. Set title, must-have skills, and candidate count from 5 to 10. Add location and remote (onsite, hybrid, or remote) when you know them. Description, responsibilities, preferred qualifications, and perks are optional.
5. Press **Send** (or Ctrl+Enter / Cmd+Enter). Your line appears in the transcript before the report exists.
6. If the gate needs more detail, the page says the crew was not started and lists the gaps. The form text stays. Add the missing pieces, or use run anyway when the gap says that is allowed.
7. When a run is accepted, status names the current task: `research_candidates`, `match_and_score`, `draft_outreach`, then `compile_report`. The page polls about every 2 seconds.
8. On completion, the transcript shows the report as markdown: job requirements, assumptions when the run continued with confirmed gaps, profiles, scores, outreach drafts, sources, and recommendations. Use **Copy** or **Download .md**. QA could not confirm clipboard or the file save in the automation browser. Retry those in your own browser.

Screenshots are not included.

## 5. Everyday Use

| Task | What you should see |
|------|---------------------|
| Empty title or empty must-haves | `422` `VALIDATION`. Retry and edit stay available. The crew does not start |
| Missing seniority or location | `needs_clarification`. Status says the crew has not started |
| Vague must-have only (for example “good culture fit”) | `VALIDATION` after the vague phrase is removed, including when run anyway is set |
| Second send while a crew is running | `409` `CREW_BUSY` |
| Completed report | Ranked leads with a source URL or an unverified mark. Outreach text states it was not sent |
| Provider or Serper key missing | `503` `MISSING_API_KEY`. Fix `.env` and restart the API |
| Unknown or expired run | `404` with message `Unknown run id.` |

Scores and drafts are input for your review. They are not a hiring decision. Do not treat a missing email or phone as a contact the model invented; the report should leave those unverified.

Candidate count on the form overrides the `CANDIDATE_LIMIT` default for that request. The allowed range is 5–10.

## 6. Troubleshooting

| Problem | What to try |
|---------|-------------|
| Page loads, status never moves | Confirm the API process is the one you started after the last `.env` edit |
| `MISSING_API_KEY` | Set the key for `LLM_PROVIDER` and set `SERPER_API_KEY`. Restart |
| Run disappears after a restart | Expected. Memory is process-local. Submit again. Older ids return `Unknown run id.` |
| Browser closed mid-run | The kickoff continues until it finishes or you stop the API |
| Copy failed | Use Download `.md`. QA saw this in the automation browser |
| Warning about function callbacks | CrewAI serialization notice. `/health` can still be ok |
| Timeout | The run stops at the supervisor limit and names the last task |
| Docker command missing | Use the two local processes. See deploy.md |

Logs: the API process stdout and `logs/trace.log` (level `LOG_LEVEL`, default INFO). `/health` is recorded only at DEBUG. Secret values are redacted when they appear in those lines. Request bodies are not written there. Optional reports stay in `var/runs/`. The Application Crew runs with CrewAI `tracing=True`. Set `CREWAI_TRACING_ENABLED=false` to turn that off. Dashboard links need `crewai login`. Full operator detail is in deploy.md.

## 7. Deployment Notes (operators)

The runbook is `project-context/3.deliver/deploy.md`. It covers the env matrix, loopback binding, compose, CI, and rollback.

Rollback, short form: stop the processes or `docker compose down`, check out the previous revision, reinstall if dependency pins changed, start again. In-memory runs are not restored. Files already saved under `var/runs/` stay on disk. Nothing in this guide performs a remote deploy.

## Sources

- `project-context/1.define/prd.md`
- `project-context/2.build/setup.md`
- `project-context/2.build/integration.md`
- `project-context/2.build/qa.md`
- `project-context/3.deliver/deploy.md`
- `.cursor/templates/user-guide-template.md`
- `security.md` is not in the repo

## Assumptions

- Local URLs and the two-process start match setup.md and integration.md.
- The sample requisition button matches `exampleDraft()` in the frontend.
- Docker steps are documented for later use. They were not executed here.
- No model call was made while writing this guide.

## Open Questions

1. Clipboard and `.md` download still need a confirmation in the operator’s browser (QA AC-006).
2. The first live crew run is still outstanding.
3. Security assessment is not written.

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

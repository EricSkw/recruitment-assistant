# Deploy — Recruitment Assistant

Release **0.1.0** of the local MVP. The runtime is CrewAI. This file is the operator runbook. No live host was provisioned and no image was pushed.

## Release readiness

Actions: `*prepare-release`.

| Gate | Status |
|------|--------|
| `project-context/2.build/qa.md` | Present. Dated 2026-10-24. Backend pytest 37 passed. Frontend Vitest 5 passed. `tsc --noEmit` passed. Chat smoke passed for empty input, validation, and clarification against the live API. The completed report was shown only against a local mock of the run API. |
| QA result | MVP verification with **scoped known gaps**. Not a clean pass of every acceptance id. AC-009 is **Fail** in that artifact. AC-003, AC-004, AC-005, and AC-012 were not proven on a live crew kickoff. |
| `project-context/2.build/security.md` | **Absent.** Accepted gap for this Tier-0 mini-project. The operator asked Deliver to proceed and to record that gap. Example config `aamad.config.example.yml` sets `security.require_security_assessment: true`. There is no project `aamad.config.yml`. |
| Runtime | `AAMAD_TARGET_RUNTIME=crewai`. Adapter: `.cursor/rules/adapter-crewai.mdc`. |

Deliver continues because `qa.md` exists and the operator accepted the missing security assessment. A later `@security.eng` pass is still the right next control before any shared or remote host.

### Release scope (0.1.0)

In this package:

- Sequential crew: researcher → matcher → communicator → reporter (`src/backend/config/agents.yaml`, `src/backend/config/tasks.yaml`).
- FastAPI on port 8000: `GET /health`, `POST /api/runs`, `GET /api/runs/{run_id}`.
- Chat UI (Vite/React) for one recruiter on the same machine.
- Clarify-before-kickoff, one active crew (`409 CREW_BUSY`), recommend-only copy, outreach drafts not sent.
- LLM switch: `LLM_PROVIDER=openai` or `grok`. Web search: `SERPER_API_KEY`.

Not in this release:

- Live cloud deploy, SSO, RBAC, ATS export, email send, LinkedIn login, database, streaming, PDF, durable report history.
- A proven live Grok/OpenAI + Serper requisition (QA known gap).
- Security assessment artifact.

Version source: `src/backend/recruitment/__init__.py` (`0.1.0`) and `src/frontend/package.json` (`0.1.0`). Image tag: `recruitment-assistant:0.1.0`.

## Hosting

Action: `*define-deploy`. Smallest SAD target: one local CPU process, port **8000**, health **`GET /health`**. No GPU. No multi-region. No IaC beyond the image and compose file.

Two operator paths:

| Path | What runs | Chat URL | API |
|------|-----------|----------|-----|
| Local Python script | Repo-root `python main.py`, then the Vite dev server | `http://127.0.0.1:5173/` | `http://127.0.0.1:8000` (Vite proxies `/api` and `/health`) |
| Docker (defined here, not built in this session) | One container. Uvicorn loads `deploy/static_app.py`, which mounts the existing API and the built `dist/` | `http://127.0.0.1:8000/` | Same origin |

`src/backend/main.py` still starts the API when the working directory is `src/backend`. The repo-root `main.py` is the same server with `app_dir` set, so `python main.py` works from the repo root. Pins are `requirements.txt` (same list as `src/backend/requirements.txt`). The container does not call `main.py`. Inside a container that loopback address is not reachable from the published port, so `deploy/entrypoint.sh` starts Uvicorn on `0.0.0.0` and `${PORT:-8000}`. Compose publishes **`127.0.0.1:8000:8000`**, so the workstation still exposes loopback only (SAD AD-08).

`deploy/static_app.py` is packaging. It does not change the crew, the gate, or the API routes. FastAPI still does not serve `dist/` when you start `main.py`. That matches the QA note that local use is two processes.

Files added:

- `Dockerfile` — Node 18 builds the frontend; Python 3.12-slim installs the repo-root `requirements.txt` and runs the entrypoint.
- `main.py` — local entry point. From the repo root: `python main.py`.
- `requirements.txt` — pinned Python dependencies for that command and for the image.
- `docker-compose.yml` — one service, env file `.env`, volume `./var/runs:/app/var/runs`.
- `.dockerignore` — excludes `.env`, `.venv`, `node_modules`, and `project-context`.
- `deploy/entrypoint.sh`, `deploy/static_app.py`.
- `.github/workflows/ci.yml` — lint, test, and build only (`*configure-cicd`). No deploy job.

Docker Desktop is not integrated in this WSL distro (`docker` is not usable). The image was **not** built and **not** started. Routing of the wrapper was checked in-process: `GET /health` returned `200 {"status":"ok"}`, `GET /` returned the built `index.html`, and an unknown run id returned `404` with message `Unknown run id.`

## Environment variable matrix

Names only, from `.env.example` and SAD §4. Set values in an untracked `.env`. Do not commit that file. Compose `environment` overrides the file for the keys it sets (`AAMAD_TARGET_RUNTIME`, `CREWAI_TELEMETRY_OPT_OUT`, `APP_ENV`, `PORT`).

| Name | Required | Purpose |
|------|----------|---------|
| `LLM_PROVIDER` | no (default `openai`) | `openai` or `grok` for the whole process |
| `OPENAI_API_KEY` | when `LLM_PROVIDER=openai` | OpenAI LLM |
| `OPENAI_MODEL` | no (default `gpt-4o`) | OpenAI model id |
| `XAI_API_KEY` | when `LLM_PROVIDER=grok` | xAI key. `GROK_API_KEY` is an accepted alias |
| `GROK_MODEL` | no (default `grok-4.7`) | Grok model id. Base URL `https://api.x.ai/v1` |
| `SERPER_API_KEY` | yes, to start a crew | Web search. `/health` still works if it is empty |
| `AAMAD_TARGET_RUNTIME` | yes (`crewai`) | Adapter selection |
| `CREWAI_TELEMETRY_OPT_OUT` | no (recommend `true`) | CrewAI telemetry |
| `APP_NAME` | no | Log label |
| `APP_ENV` | no | `development` or `production` |
| `CANDIDATE_LIMIT` | no (default `10`) | Default N when the request omits it |
| `HOST` | no (default `127.0.0.1`) | Bind address for `main.py` only. The container entrypoint ignores it |
| `PORT` | no (default `8000`) | Bind / listen port |

Do not add `LINKEDIN_COOKIE`. The chat page reads `VITE_API_BASE` only when the UI must call another origin. Leave it unset for the Vite proxy and for the container (same origin).

Copy the example before first start:

```bash
cp .env.example .env
```

Fill the key for the selected provider and `SERPER_API_KEY`. Restart the API after any `.env` change. The process does not reload the file.

## Install, start, stop, roll back

Action: `*document-deploy`.

### Install (local)

From the repo root. Python 3.12. Node 18 (Linux Node inside WSL; do not use a Windows `npm` against this path).

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cd src/frontend && npm ci
```

### Start (local Python script)

From the repo root, with the virtualenv activated:

```bash
source .venv/bin/activate
python main.py
```

That listens on `http://127.0.0.1:8000` (`HOST` / `PORT`). It does not serve the chat page. In a second terminal:

```bash
cd src/frontend && npm run dev
```

Check:

```bash
curl -sS http://127.0.0.1:8000/health
curl -sS http://127.0.0.1:5173/health
```

Both should return `{"status":"ok"}`. Open `http://127.0.0.1:5173/`.

### Stop (local)

Ctrl+C in each terminal. An in-flight kickoff stops with the API process. Run records are in memory and are gone. Optional report files already written under `var/runs/` stay on disk.

### Install and start (Docker)

Requires Docker Compose v2. Not executed in this session.

```bash
cp .env.example .env
mkdir -p var/runs
docker compose build
docker compose up
```

Check: `curl -sS http://127.0.0.1:8000/health` and open `http://127.0.0.1:8000/`.

`PORT` inside the container is forced to `8000`. Changing `PORT` in `.env` does not move the published port. Changing `HOST` in `.env` does not change the container bind.

### Stop (Docker)

```bash
docker compose stop
```

`docker compose down` removes the container. The `var/runs` directory on the host remains. The image `recruitment-assistant:0.1.0` remains until removed.

### Roll back

There is no remote release and no database migration.

1. Stop the local processes or run `docker compose down`.
2. Check out the previous git revision of the repo.
3. If `requirements.txt` or `src/frontend/package-lock.json` changed, reinstall (local) or `docker compose build` (container). `src/backend/requirements.txt` carries the same pins.
4. Start again using the steps above.
5. Expect polls for run ids from the old process to return `404` `Unknown run id.` In-memory state is not restored.

To keep the current checkout and only leave the container stopped, `docker compose stop` is enough. To drop a bad local image tag after a rebuild, `docker image rm recruitment-assistant:0.1.0` and build again from a known commit.

## Access control (MVP)

- One operator on one machine. No login, SSO, or RBAC (PRD AuthN/Z).
- Local API binds `127.0.0.1`. Compose publishes `127.0.0.1:8000` only. Do not change the publish address to `0.0.0.0` on a shared network.
- Browser CORS allows only `http://127.0.0.1:5173` and `http://localhost:5173`. The container UI is same-origin and does not need a third origin.
- Secrets are environment variables. Logs redact `OPENAI_API_KEY`, `XAI_API_KEY`, `GROK_API_KEY`, and `SERPER_API_KEY` when those values appear in a log line.
- The crew may send candidate names and public URLs to the configured LLM and to Serper. Reports can be written under `var/runs/`. There is no shared candidate database.
- The product recommends. It does not reject, advance, or send outreach. `POST /api/send`, `/api/reject`, `/api/advance`, and `/api/ats` are not implemented.
- The container runs as root. That is an MVP image limit. The host port is still loopback-only.
- Least privilege for keys: a provider key that can call the selected chat model, and a Serper key that can search. No deployment credential is stored in the repo. CI has no cloud credentials and no deploy job.

## Monitoring and logging

Baseline only. No APM, no uptime SLA (NFR-004).

| Signal | Where |
|--------|--------|
| Liveness | `GET /health` → `{"status":"ok"}`. Also the image `HEALTHCHECK` and the compose healthcheck |
| API access | Uvicorn on stdout. Container: `docker compose logs` |
| Run events | Logger name `recruitment`. Appended to `project-context/2.build/logs/trace.log` (created on demand). In the container that path is inside the writable layer unless you mount it. It is not the same as stdout |
| Prompt trace | `project-context/2.build/logs/prompt-trace.md`, rewritten when crew config is loaded |
| Optional reports | `var/runs/*.md` (gitignored). Compose mounts this directory |

Startup can log a CrewAI warning that function callbacks cannot be serialized. QA recorded that `/health` still returns ok.

## CI

`.github/workflows/ci.yml` on push and pull request:

- Backend: Python 3.12, `pip install -r requirements.txt`, `compileall` of `src/backend` and `deploy`, `pytest` in `src/backend`.
- Frontend: Node 18, `npm ci`, `npm test`, `npm run lint` (`tsc --noEmit`), `npm run build`.

Ruff is not a project dependency. Syntax compile plus the existing test and typecheck commands are the lint stage. The workflow does not deploy.

## Troubleshooting

| Symptom | What to do |
|---------|------------|
| `503` `MISSING_API_KEY` | The selected provider key or `SERPER_API_KEY` is missing or empty. Edit `.env` and restart the API. Key checks run before the clarify gate, so the gap list is not shown. |
| `422` `VALIDATION` | Title, must-haves, or candidate count failed the gate. Count must be 5–10. Vague-only must-haves are stripped. The form text stays. |
| `needs_clarification` and “The crew was not started.” | Seniority or location is missing. Add them, or use the allowed run-anyway path. `run_id` is null. |
| `409` `CREW_BUSY` | One crew is already active in this process. Wait, or restart the API to abandon it. Closing the browser does not cancel the kickoff. |
| `404` `Unknown run id.` | The process restarted, or the id is wrong. Start a new run. |
| `/health` ok, chat cannot connect | Local: Vite must be on port 5173 and the API on port 8000. Container: open port 8000, not 5173. The image does not run Vite. |
| Worked yesterday, blank page in Docker | The frontend image stage failed or `dist/` was empty. Rebuild with `docker compose build`. Local `main.py` never serves `dist/`. |
| CrewAI callback serialization warning | Expected with this CrewAI pin. Confirm `/health`. |
| Long run then `TIMEOUT` | Supervisor limit is 480 seconds (NFR-001). The error names the last task. Partial text, when present, is labeled. |
| Suspected leaked key | QA AC-009: `.env.example` previously held a non-placeholder `XAI_API_KEY`. Rotate that key at the provider. This Deliver read of `.env.example` shows placeholder text only (`your_grok_key_here`, `your_openai_api_key_here`, empty `SERPER_API_KEY`). That observation is not a new QA pass. |
| `docker` not found | Enable Docker Desktop WSL integration, or use the local two-process path. |

## Future work

- Security assessment (`security.md`), including trace redaction and the LinkedIn denylist.
- One operator requisition with a real provider key and `SERPER_API_KEY` after any exposed key is rotated.
- Build and smoke the image once Docker is available.
- Ruff (or another configured linter) if the operator wants it in CI.
- APM, autoscaling, queues, multi-region, SSO, and a non-root container user.
- P1/P2 product items from the PRD (history, streaming, PDF, ATS, send).

## Sources

1. `project-context/1.define/prd.md` — infrastructure, AuthN/Z, NFR-004, NFR-007, NFR-008, Phase 3 (no live deploy).
2. `project-context/1.define/sad.md` — AD-08, §4 environment names, §5 DevOps and Deployment Architecture.
3. `project-context/2.build/qa.md` — verification result, AC-009, known gaps.
4. `project-context/2.build/backend.md`, `frontend.md`, `integration.md`, `setup.md`.
5. `.cursor/agents/devops-eng.md`, `.cursor/rules/delivery-workflow.mdc`, `.cursor/rules/adapter-crewai.mdc`.
6. `aamad.config.example.yml` (`security.require_security_assessment`, `documentation.require_user_guide`). No project `aamad.config.yml`.
7. `.env.example` (names and placeholders only).
8. `src/backend/main.py`, `src/backend/requirements.txt`, `src/backend/recruitment/__init__.py`, `src/frontend/package.json`.

## Assumptions

- The operator accepted the missing `security.md` for this Tier-0 delivery. Example-config assessment is still required before a shared host.
- QA’s scoped gaps and the AC-009 fail are the release record. Placeholder text in `.env.example` at write time does not reopen that test.
- Resolved runtime is `crewai` from the operator request, `.env.example`, the PRD, and the SAD. The shell did not need to export `AAMAD_TARGET_RUNTIME` for this packaging.
- Local two-process start remains the path QA exercised. The container is the optional single service from SAD §5.
- No operator authorization was given to build, push, or deploy. Docker was not available in this distro.
- The image installs the existing `requirements.txt`, including pytest. A slimmer runtime file was not split out.
- CI uses `compileall` because Ruff is not pinned.
- This persona made no model call. Prompt Trace was not written for that reason. Importing the app during the route check did not change `prompt-trace.md` or `trace.log` (hashes matched before and after).

## Open Questions

1. Who runs `@security.eng` before any host that is not this operator’s loopback?
2. After the historical `XAI_API_KEY` exposure is rotated, who runs the first live requisition?
3. Should a project `aamad.config.yml` be copied from the example before the next epic?
4. Once Docker Desktop is integrated, should the operator treat the container UI as the demo path, or keep Vite on port 5173 as the only supported UI?

## Audit

- **timestamp:** 2026-10-25T16:11:22Z
- **persona id:** `devops-eng`
- **action:** `prepare-release`, `define-deploy`, `configure-cicd`, `document-deploy`
- **resolved AAMAD_TARGET_RUNTIME:** `crewai`
- **llm / temperature / max_tokens:** none. No model call. Prompt Trace omitted for that reason
- **tools:** read PRD, SAD §4–§5, qa.md, backend.md, frontend.md, integration.md, setup.md, `.env.example`, `aamad.config.example.yml`, `main.py`, `requirements.txt`, `asgi.py`; in-process `TestClient` against `deploy/static_app.py`; `docker` unavailable in this WSL distro
- **outputs:** `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `deploy/entrypoint.sh`, `deploy/static_app.py`, `.github/workflows/ci.yml`, this artifact, `project-context/3.deliver/user-guide.md`
- **deployment status:** config and runbook only. Not deployed

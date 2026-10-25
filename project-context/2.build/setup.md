# Setup — Recruitment Assistant

Environment record for the Build scaffold. Application code already lives under `src/backend` and `src/frontend`. This file documents that layout, the installed toolchains, and the environment names. It does not add product behavior.

## Layout

```
recruitment-assistant/
├── .env.example
├── .venv/                         # Python 3.12 virtualenv at the repo root
├── project-context/
│   ├── 1.define/                  # prd.md, sad.md, mrd.md
│   └── 2.build/                   # this file, frontend, backend, integration, qa
├── src/backend/                   # CrewAI package, FastAPI, pytest
└── src/frontend/                  # Vite + React chat UI
```

`var/runs/` is the optional completed-report directory from SAD §4. It is gitignored and created by the API when a run finishes.

## Python

- Interpreter: repo `.venv` (Python 3.12). CrewAI requires `>=3.10` and `<3.14`.
- Backend pins: `src/backend/requirements.txt` (crewai 1.15.28, crewai-tools 1.15.28, fastapi 0.149.0, uvicorn 0.54.0, pydantic 2.12.5, and the test pins listed there).
- The `aamad` CLI used for artifact checks is `.venv/bin/aamad`. It is not on `PATH` until the virtualenv is activated.

```bash
python3 -m venv .venv
.venv/bin/pip install -r src/backend/requirements.txt
```

## Frontend

- App root: `src/frontend`. Scripts: `npm run dev`, `npm test`, `npm run lint` (`tsc --noEmit`), `npm run build`.
- Pins in `src/frontend/package.json`: react 18.3.1, vite 5.4.11, typescript 5.6.3, vitest 2.1.8.
- QA used Linux Node at `/usr/bin/node` (v18.19.1). Windows `npm` on this machine cannot install into the WSL project path. Use the Linux Node inside WSL.

```bash
cd src/frontend && npm install
```

## Environment

Copy `.env.example` to `.env` at the repo root. The API loads that file. Names only:

| Name | Required | Purpose |
|------|----------|---------|
| `LLM_PROVIDER` | no (default `openai`) | `openai` or `grok` for the process |
| `OPENAI_API_KEY` | when `LLM_PROVIDER=openai` | OpenAI key |
| `OPENAI_MODEL` | no (default `gpt-4o`) | OpenAI model id |
| `XAI_API_KEY` | when `LLM_PROVIDER=grok` | xAI key. `GROK_API_KEY` is an alias |
| `GROK_MODEL` | no (default `grok-4.7`) | Grok model id |
| `SERPER_API_KEY` | yes, to start a crew | Web search |
| `AAMAD_TARGET_RUNTIME` | yes | `crewai` |
| `CREWAI_TELEMETRY_OPT_OUT` | no (recommend `true`) | Telemetry |
| `APP_NAME` | no | Log label |
| `APP_ENV` | no | `development` or `production` |
| `CANDIDATE_LIMIT` | no (default `10`) | Default N when the request omits it |
| `HOST` | no (default `127.0.0.1`) | Bind address |
| `PORT` | no (default `8000`) | Bind port |

Do not add `LINKEDIN_COOKIE`. Do not commit `.env`.

There is no project `aamad.config.yml`. Example preferences in `aamad.config.example.yml` apply. Copy that file only if the operator wants a project config (SAD Open Question 1).

## Run

Two processes, from the repo root:

```bash
cd src/backend && ../../.venv/bin/python main.py
cd src/frontend && npm run dev
```

The API listens on `http://127.0.0.1:8000` (`GET /health`). The chat UI is `http://127.0.0.1:5173/`. The Vite dev server proxies `/api` and `/health` to the API.

Artifact check:

```bash
.venv/bin/aamad validate --phase build
```

## Downstream epics

Frontend, backend, integration, and QA artifacts are already in `project-context/2.build/`. Next remaining Build/Deliver work is `@security.eng` (`security.md`) and then `@devops.eng` (`deploy.md`), after the operator asks for those epics.

## Sources

- `project-context/1.define/prd.md` and `project-context/1.define/sad.md` §4–§5.
- `src/backend/requirements.txt`, `src/backend/main.py`, `src/frontend/package.json`.
- `.env.example`.
- `project-context/2.build/backend.md`, `frontend.md`, `integration.md`, `qa.md`.

## Assumptions

- The scaffold is the trees those epics already created. This file records them after the fact.
- Python 3.12 in `.venv` and Linux Node v18.19.1 are the toolchains those epics used.
- `aamad.config.yml` stays absent until the operator copies the example.

## Open Questions

1. SAD Open Question 1: copy `aamad.config.example.yml` to `aamad.config.yml` before later epics?
2. SAD Open Question 5 is closed for the tool class: search is Serper, and `SERPER_API_KEY` is the name in `.env.example`.

## Audit

- timestamp: 2026-10-24T03:45:00Z
- persona id: `project-mgr`
- action: `document-setup`
- resolved AAMAD_TARGET_RUNTIME: `crewai`
- llm / temperature / max_tokens: none. No model call. Prompt Trace omitted for that reason
- tools: read PRD, SAD §4–§5, `.env.example`, backend and frontend manifests, existing build artifacts
- outputs: `project-context/2.build/setup.md`

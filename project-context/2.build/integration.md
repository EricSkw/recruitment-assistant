# Integration — Recruitment Assistant

The chat page submits a requisition to `POST /api/runs` and polls `GET /api/runs/{run_id}` every 2 seconds. Responses are not streamed. The clarify-before-kickoff decision stays on the API.

## Diagnostic

`project-context/2.build/setup.md` is not in the repository. Integration continued because the operator invoked `@integration.eng` and the PRD, SAD, frontend, and backend artifacts already define the chat contract. No product route was added to fill that gap.

## Actions

| Action | Result |
|--------|--------|
| `*integrate-api` | `src/frontend/src/api/client.ts` calls the run API. The Vite dev server proxies `/api` and `/health` to `http://127.0.0.1:8000`. The API allows the Vite origins. |
| `*verify-messageflow` | Browser send and retry against the live API. Mocked API tests cover accept, clarification, busy, and poll. |
| `*log-integration` | This file |

## Contract

Runtime is CrewAI behind the FastAPI app. The browser never imports the crew.

| Item | Agreement |
|------|-----------|
| Base URL | Same origin. Dev server proxies to `http://127.0.0.1:8000`. `VITE_API_BASE` overrides the prefix when set |
| Submit | `POST /api/runs` with the SAD JSON body |
| Accept | `202` `{"run_id","status":"queued","gaps":[]}` |
| Clarification | `200` `needs_clarification`, `run_id` null, no kickoff |
| Errors | Envelope `error.code`, `error.message`, `error.run_id` |
| Poll | `GET /api/runs/{run_id}` every 2 seconds until `completed`, `failed`, or `partial` |
| Streaming | None |
| Active runs | One. A second submit is `409` `CREW_BUSY` |

The page paints the user message before the response returns. On clarification it lists each gap and offers run anyway only when every gap allows it. Run anyway resubmits the same body with `confirm_run_anyway: true`. On a terminal run it renders `report_markdown` and lists `assumptions`. On an error it shows `error.code` and `error.message` and leaves the form text in place.

An unreachable API, or a body the page cannot read, is shown as `CREW_FAILURE` with an operator-safe message. A poll that is not a run record stops the loop and shows the envelope. Unknown ids keep the API message `Unknown run id.`

## Wiring

| Path | Change |
|------|--------|
| `src/frontend/src/api/client.ts` | HTTP client |
| `src/frontend/src/api/client.test.ts` | Fetch contract checks |
| `src/frontend/src/session/useChatSession.ts` | Submits without a preview mode |
| `src/frontend/src/components/Composer.tsx` | Fixture preview control removed |
| `src/frontend/src/App.tsx` | Footer states that the page calls the API |
| `src/frontend/vite.config.ts` | Proxy `/api` and `/health` |
| `src/backend/recruitment/api.py` | CORS for `http://127.0.0.1:5173` and `http://localhost:5173` |
| `src/backend/tests/test_api.py` | Preflight from the Vite origin is allowed. Another origin is not |

Removed with the stub: `src/frontend/src/api/previewGate.ts`, `src/frontend/src/api/fixtures.ts`, and the `yaml` dependency. YAML paste is sent as `raw_blob`. The API parses it.

`project-context/2.build/frontend.md` still describes the fixture client. This artifact supersedes that client description.

## Verification

Checked on 2026-10-23. No crew kickoff. The operator `.env` has `LLM_PROVIDER=grok`, an `XAI_API_KEY`, and `SERPER_API_KEY`. The API process was restarted after the search key was added. The live request below omits seniority and location, so the gate returns clarification and does not call the crew.

| Check | Result |
|-------|--------|
| `GET /health` on port 8000 | `200` `{"status":"ok"}` |
| `POST /api/runs` through the Vite proxy | `200` `needs_clarification` for missing seniority and location. An earlier process, started before `SERPER_API_KEY` was set, returned `503` `MISSING_API_KEY` |
| CORS preflight from `http://127.0.0.1:5173` | `200`, allow-origin echoes that origin |
| Browser at `http://127.0.0.1:5173/` | The same requisition shows “The crew was not started,” with seniority and location gaps and Run anyway allowed. Title and must-haves stay in the form. Run anyway was not clicked. Fixture preview is gone |
| `npm test` in `src/frontend` | 5 passed. Covers `202`, clarification, `422`, `409`, `503`, poll, unknown id, unreachable API |
| `npm run lint` | `tsc --noEmit` passed |
| `pytest` in `src/backend` | 37 passed, including the new CORS check and the existing mocked accept, clarification, busy, timeout, and partial cases |

A completed report was not requested. That path calls the configured LLM and Serper. The mocked suite already walks a run to a terminal status without those calls.

## Known issues

1. A completed search was not run. Run anyway, or a requisition that already includes seniority and location, starts the crew and calls Grok and Serper.
2. Key checks run before the clarify gate. If a required key is missing, the page shows `503` `MISSING_API_KEY` instead of the gap list. The API must be restarted after `.env` changes.
3. `setup.md` is still absent.
4. `frontend.md` is stale on the client. Read this file for the wired behavior.
5. FastAPI does not serve `src/frontend/dist/`. Local use is two processes. Serving the built page is Deliver work.
6. CORS is limited to the two Vite origins. A browser on another origin cannot call port 8000.
7. Run state is in process memory. After a restart, a poll for an old id returns `404` `Unknown run id.`
8. Closing the page does not cancel a kickoff. The operator restarts the API process.
9. CrewAI logs a warning that function callbacks cannot be serialized. The process still starts and `/health` returns ok.

## How to run

Two processes, from the repo root:

```bash
cd src/backend && ../../.venv/bin/python main.py
cd src/frontend && npm install && npm run dev
```

Open `http://127.0.0.1:5173/`. The API listens on `http://127.0.0.1:8000`. Set `VITE_API_BASE` only when the page should call the API host directly instead of the proxy.

Both processes were left running after this verification.

## Sources

1. `project-context/1.define/prd.md` (product-mgr, 2026-10-16), chat scope and the CrewAI runtime.
2. `project-context/1.define/sad.md` (system-arch, 2026-10-19), §3 states, §4 HTTP contract, §6 request path.
3. `project-context/2.build/frontend.md` (frontend-eng, 2026-10-23). The fixture client described there is replaced by this epic.
4. `project-context/2.build/backend.md` (backend-eng), gate order, error envelope, and poll body.
5. `.cursor/agents/integration-eng.md` actions `integrate-api`, `verify-messageflow`, `log-integration`.
6. `.cursor/rules/adapter-crewai.mdc`. The HTTP layer calls the existing crew entrypoint. Agents and tasks stay in YAML.

## Assumptions

- Missing `setup.md` does not change the SAD request path. The app remains `src/frontend` and `src/backend`.
- A same-origin dev proxy is the MVP wiring. Direct calls from the Vite origin are also allowed.
- Deleting the local gate copy is in scope. `src/backend/recruitment/gate.py` is the only gate.
- The live clarification response is the basic round-trip. A paid kickoff was not required to prove the wire.
- No `aamad.config.yml`. Resolved runtime is `crewai` from `.env` and `.env.example`.
- This persona made no model call. Prompt Trace was not written for that reason. API startup still uses the backend crew loader, which refreshes `project-context/2.build/logs/prompt-trace.md`. Checked logs do not contain secret values.

## Open Questions

1. `setup.md` now records the environment and accepts `src/frontend` and `src/backend` as the scaffold.
2. SAD Open Question 5: Serper is the search tool, and `SERPER_API_KEY` is now set. A live search still has not been run.
3. Should a missing key return after the clarify gate, so the recruiter sees gaps first? The API checks keys first. This epic follows that order.
4. Deliver still needs to decide whether FastAPI serves `dist/` or the two-process layout remains the operator path.

## Audit

- **timestamp:** 2026-10-23T04:39:30Z
- **revision:** 2026-10-23T04:39:30Z — recheck after `SERPER_API_KEY` was set; API restarted; live result is `needs_clarification`
- **persona id:** `integration-eng`
- **action:** `integrate-api`, `verify-messageflow`, `log-integration`
- resolved AAMAD_TARGET_RUNTIME: `crewai` (`.env`, `.env.example`, PRD, SAD)
- **llm / temperature / max_tokens:** none for this persona. No model call. Prompt Trace omitted for that reason
- **tools:** read PRD, SAD §3–§6, frontend.md, backend.md, API and chat client; `npm test`, `tsc --noEmit`, `pytest` (37 passed); live `GET /health` and `POST /api/runs` via the Vite proxy; browser session on `http://127.0.0.1:5173/`
- **outputs:** wired client, CORS and proxy, this artifact

# Frontend — Recruitment Assistant

MVP chat page for one requisition at a time. The page collects a job as fields or a YAML paste, shows the clarify-before-kickoff gaps, and renders a recruiter report with copy and markdown download.

The API is not connected. `src/frontend/src/api/client.ts` is a fixture client. `@integration.eng` replaces that module with the real base URL and poll loop.

## Diagnostic

`project-context/2.build/setup.md` is not in the repository. `@project.mgr` has not recorded the Vite skeleton. Implementation continued because the operator invoked `@frontend.eng` and the PRD plus SAD already specify the chat, the states, and the request shapes. No product route or feature was added to fill that gap.

## Actions

| Action | Result |
|--------|--------|
| `*develop-fe` | Vite + React 18 + TypeScript chat at `src/frontend/` |
| `*style-ui` | System theme, minimal CSS, readable below 768px. Tailwind was not used |
| `*add-placeholders` | Not applied. SAD §3 says Future Work (ATS, send, SSO) is not shown |
| `*document-frontend` | This file |

## Stack

SAD AD-04 is the UI contract: Vite, React 18, TypeScript strict, no component library, one route `/`.

| Concern | Choice |
|---------|--------|
| App | `src/frontend/` |
| Route | `/` only |
| State | React state plus `src/frontend/src/session/useChatSession.ts` |
| Styling | `src/frontend/src/styles.css`. `color-scheme: light dark` |
| Markdown | Small renderer in `MarkdownReport.tsx`. No raw HTML |
| YAML paste | `yaml` package, used only by the fixture gate |

The frontend persona text says Next.js and Tailwind. The PRD and SAD override that. See Open Questions.

## Screen

The banner stays at the top of the page:

> Recommendations require human review. This app does not reject or contact candidates.

Composer, one mode at a time:

- Fields: title, must-have skills, description, responsibilities, preferred qualifications, location, remote, perks.
- Paste: one YAML blob. Explicit fields are not sent in this mode. The fixture still lets tests merge a blob with explicit fields, matching SAD §4.
- Candidate count 5–10, default 10.
- Send, or Ctrl+Enter / Cmd+Enter.
- The requisition stays in the form after an error. Edit moves focus to the title or the paste box. Retry resubmits the last request.

| State | What the page does |
|-------|--------------------|
| Empty | Short instructions. Status: “No run yet.” |
| Needs clarification | Lists each gap and whether run anyway is allowed. Does not show a running task. |
| In progress | User message is already in the transcript. Status names `research_candidates`, `match_and_score`, `draft_outreach`, or `compile_report`, with the recruiter-facing role. Send is disabled. |
| Error | Shows `error.code` and `error.message`. Retry and Edit. Form text remains. |
| Completed | Assistant message is the report, rendered as headings and lists, plus Copy and Download `.md`. Partial results are labeled Partial. Assumptions from the run are listed. |

Run anyway resubmits the same fields with `confirm_run_anyway: true`. It does not replace the requisition with the words “run anyway”.

A collapsed “Fixture preview” control selects sample report, missing key, busy, timeout, guardrail, partial, zero public hits, or crew load failure. It exists so the states can be seen without the API. Integration should remove it when the real client lands.

## Fixture client

`submitRun` and `getRun` return the SAD envelopes and never call `fetch`.

- Empty title or empty must-haves (after the vague-phrase strip) return `422` `VALIDATION`. Run anyway does not bypass them.
- Missing seniority or location returns `200` `needs_clarification` and does not create a run.
- A passing request returns `202` `queued`. Each `getRun` projects the clock: queued, then the four task ids, then a terminal fixture. The page polls every 2 seconds.
- A second request while one run is queued or running returns `409` `CREW_BUSY`.
- The sample report is layout text. The only lead is “Fixture Lead A” at `https://example.com/fixture-lead-a`. It is not a live search and not a hiring decision. The report includes the required headings and the words “not sent”.

The preview gate mirrors the published backend rules so the chat can demonstrate AC-010 and AC-011. The backend gate remains the source of truth after integration.

## Files

| Path | Purpose |
|------|---------|
| `src/frontend/index.html` | Page shell |
| `src/frontend/src/App.tsx` | Banner, transcript, status, composer |
| `src/frontend/src/components/ChatTranscript.tsx` | Messages, copy, download |
| `src/frontend/src/components/Composer.tsx` | Fields or paste, send |
| `src/frontend/src/components/RunStatus.tsx` | Task label, gaps, errors |
| `src/frontend/src/components/MarkdownReport.tsx` | Report rendering |
| `src/frontend/src/api/client.ts` | Fixture client. Integration replaces this |
| `src/frontend/src/api/previewGate.ts` | Local preview of the clarify gate |
| `src/frontend/src/api/fixtures.ts` | Sample and partial markdown |
| `src/frontend/src/session/useChatSession.ts` | Transcript and poll |
| `src/frontend/src/api/client.test.ts` | Gate and client checks |

## How to run

From `src/frontend/`, with a Linux Node.js that can see this path (npm 18+ is enough; the commands below were run with Node 20):

```bash
npm install
npm test
npm run lint
npm run build
npm run dev
```

Dev server: `http://127.0.0.1:5173/`. `npm run lint` is `tsc --noEmit`. Production build writes `src/frontend/dist/` (gitignored).

## Tests

`npm test` — 12 passed on 2026-10-23.

| Check | What it locks |
|-------|----------------|
| Empty title, vague must-haves | AC-011 hard block, including when run anyway is set |
| Missing seniority and location | Clarification, no run id |
| Run anyway | Assumption strings |
| Task poll | The four task ids, then a report that contains “not sent” and does not start with a code fence |
| Timeout | Message names `research_candidates` |
| Missing key | `503` `MISSING_API_KEY` |
| Second submit | `409` while a run is active |
| `fetch` | The stub throws if `fetch` is called |

A browser pass on `http://127.0.0.1:5173/` covered empty submit, clarification, run anyway through the task labels to the rendered report, missing-key error with the form text kept, Edit focusing the title, Ctrl+Enter on an invalid paste, and a 390px-wide layout. Copy and download are on the completed report; the clipboard write itself was not confirmed in that pass.

## Sources

1. `project-context/1.define/prd.md` (product-mgr, 2026-10-16), P0-7, P0-10, P0-11, NFR-002, NFR-015, NFR-016, §6.
2. `project-context/1.define/sad.md` (system-arch, 2026-10-19), §3 frontend, §4 request and error shapes, AD-04, AD-05.
3. `.cursor/agents/frontend-eng.md` actions `develop-fe`, `add-placeholders`, `style-ui`, `document-frontend`.
4. `aamad.config.example.yml` (no project `aamad.config.yml`): system theme, minimal style, no modals, type checking, 400-line cap.
5. `project-context/2.build/backend.md` for the gate messages and the poll contract the stub previews.

## Assumptions

- Missing `setup.md` does not change the SAD UI contract. The Vite app lives at `src/frontend/`.
- No `aamad.config.yml`. Example UI preferences apply. PRD and SAD stay authoritative over the persona’s Next.js and Tailwind lines.
- The fixture gate may drift from `src/backend/recruitment/gate.py` until integration deletes it. Behavior here matches that file as of this build.
- Candidate count is on the form because the request schema includes `candidate_limit` (5–10, default 10).
- Jurisdiction banner stays out (SAD Open Question 3).
- No model call was made for this epic, so Prompt Trace was not written.
- `npm run lint` is the TypeScript check. A separate ESLint config is left for the Deliver CI scaffold.

## Open Questions

1. `setup.md` now records the frontend toolchain and accepts `src/frontend` as the scaffold.
2. The frontend persona says Next.js and Tailwind. SAD AD-04 says Vite, React, and semantic CSS. This build follows the SAD. Change only if the SAD is revised.
3. Should the fixture preview control ship in the operator build, or only in dev? It is visible, collapsed, and labeled. Integration can delete it with the stub client.
4. Windows `npm` on this machine cannot install into the WSL path. Use a Linux Node. That belongs in `setup.md`.

## Audit

- **timestamp:** 2026-10-23T03:53:10Z
- **persona id:** `frontend-eng`
- **action:** `develop-fe`, `style-ui`, `document-frontend`
- **resolved AAMAD_TARGET_RUNTIME:** `crewai` (PRD, SAD, `.env.example`). The page does not import the crew
- **llm / temperature / max_tokens:** none. No model call. Prompt Trace omitted for that reason
- **tools:** read PRD §4 and §6, SAD §3 and §4, frontend persona, backend gate and API; `npm test` (12 passed), `tsc --noEmit`, `vite build`; browser session on `http://127.0.0.1:5173/`
- **outputs:** `src/frontend/` and this artifact
- **libraries:** react 18.3.1, react-dom 18.3.1, yaml 2.6.1, vite 5.4.11, typescript 5.6.3, vitest 2.1.8

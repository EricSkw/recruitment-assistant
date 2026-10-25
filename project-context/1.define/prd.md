# Product Requirements Document — Recruitment Assistant

**Deep Research Report / MRD**: `project-context/1.define/mrd.md`  
**System Description**: N/A (`*elicit-requirements` not run; stakeholder provided the CrewAI recruitment example as the use case)  
**System Concept**: Chat-operated multi-agent copilot that, given a job requisition, researches public candidate leads, scores them against the requisition, drafts outreach templates, and compiles a recruiter report — following the CrewAI “AI Crew for Recruitment” workflow.  
**Selected Runtime**: `crewai`

---

## 1. Executive Summary

### Problem Statement

Recruiters filling professional/technical roles still spend days on first-pass **sourcing, scoring, and first-touch copy**. SHRM 2025 reports screening and interviewing each averaging 8–9 days, median time-to-fill of about 1.5 months, and nonexecutive cost-per-hire of USD 5,475 (executive USD 35,879). Informal ChatGPT use is un-auditable; full ATS suites do not run an inspectable research→score→outreach-draft→report crew; the public CrewAI recruitment example is CLI-only and includes a LinkedIn cookie tool the authors warn may violate LinkedIn’s terms of service.

**Target users:** in-house or agency recruiters and hiring managers (SME/startup technical hiring). Not a consumer job board. Market-facing *capability*; GTM optional (see §9).

### Solution Overview

A **sequential four-agent CrewAI crew** behind a **minimal chat UI**:

1. **Researcher** — public-web candidate leads (default up to 10, cost-tunable).  
2. **Matcher** — ranked scores with written justifications against a published rubric.  
3. **Communicator** — outreach *templates only* (no send).  
4. **Reporter** — one markdown report for the recruiter (profiles, scores, outreach, sources).

**Differentiators:** YAML-inspectable agents/tasks; ToS-safe sourcing (no authenticated LinkedIn scrape); human-gated recommendations; AAMAD-traceable MVP (chat + kickoff + tests).

**Expected outcomes:** minutes-to-hours to a reviewable shortlist instead of a full day of Boolean search and copywriting; **≥ 3 hours/week** saved per active recruiter on first-pass sourcing, scoring, and outreach drafting (see §7); every listed candidate has a source URL or is marked unverified; zero automated hire/reject or outbound messages.

### Strategic Rationale

Multi-agent sequential orchestration matches the domain: research must complete before scoring; scoring and outreach both feed a single report (`Task.context` in the example). A single chatbot without task contracts cannot guarantee those headings. Timing: gen-AI recruiting adoption is 37% (LinkedIn 2025) while regulators treat hiring AI as high-risk — an **assistive, explainable** copilot is the viable wedge. Runtime `crewai` is an implementation choice, not the product definition; the product is the recruitment workflow.

---

## 2. Market Context & User Analysis

### Target Market / Users

**Primary persona — Recruiter (operator)**  
Runs the assistant, owns the req, judges shortlist quality, performs real outreach in their own tools.

**Secondary persona — Hiring manager**  
Reads the report, comments on must-haves; may not kick off runs.

**Buyer (later)** — TA/people-tech lead; needs logs and policy. Not an MVP login role.

**Segment:** SME/startup and small TA teams hiring professional/technical roles (the example uses a Rails/React engineer req). Geography: English-first; North America/Europe as research focus (MRD). Expansion, localization, and high-volume hourly hiring are N/A for MVP.

### User Needs Analysis

| Pain | Product response |
|------|------------------|
| Slow first-pass sourcing | Researcher + search/scrape tools |
| Inconsistent “gut” ranking | Matcher + explicit rubric + justifications |
| Blank-page outreach | Communicator templates |
| No single artifact for the HM | Reporter markdown |
| Legal/ToS fear | No cookie scraping; no auto-send; recommend-only language |
| Hallucinated people | Source URL required; contact unknown if missing |
| Ambiguous or incomplete req | Clarify-before-kickoff or labeled Assumptions; never invent must-haves |

**Journey:** compose job req in chat → **ambiguity check** (clarify or refuse empty/critical gaps) → confirm kickoff → watch task progress → receive report (including any run-time Assumptions) → copy/export → human outreach outside the app.

**Adoption:** succeed if the first run on a real req produces at least a few URL-backed leads and usable templates. Fail if contacts are invented or LinkedIn login is requested.

### Competitive Landscape

See MRD §1. Direct alternatives: LinkedIn Recruiter, Greenhouse/Lever/Ashby, SeekOut/Gem/Eightfold, DIY LLM. This MVP does **not** compete on ATS pipeline or people-graph scale. It competes on **transparent crew workflow + safe assistive report**.

---

## 3. Technical Requirements & Architecture

### Runtime & Agent Specifications

Aligned with `AAMAD_TARGET_RUNTIME=crewai` and `.cursor/rules/adapter-crewai.mdc`:

- Agents and tasks **MUST** live in `config/agents.yaml` and `config/tasks.yaml`.
- Sequential `Process`; **no** hierarchical manager in MVP.
- `allow_delegation=false` on all agents (matches example).
- Explicit `Task.context` on the report task (research, match, outreach).
- `expected_output` must name required report headings and “markdown without code fences” for the recruiter report.
- `memory=False`.
- `max_iter <= 12` per agent/task unless SAD justifies more.
- `max_retry_limit >= 2`.
- `max_rpm` set at crew level (SAD picks the number).
- `max_execution_time` per kickoff (SAD; operator-visible timeout).
- Secrets only from environment; names in `.env.example`.
- Do not switch function-calling vs other tool modes mid-run.

### Core Agent Definitions

**agent:** `researcher`  
- **role:** Job Candidate Researcher  
- **goal:** Find potential candidates for the specified job using public web resources  
- **tools:** web search (e.g. SerperDevTool), public website scrape  
- **runtime notes:** `allow_delegation=false`; `max_iter<=12`; **must not** include LinkedIn cookie/Selenium tools  

**agent:** `matcher`  
- **role:** Candidate Matcher and Scorer  
- **goal:** Score candidates against the job requirements with a fair, transparent rubric  
- **tools:** web search, public scrape (for evidence checks only); no LinkedIn auth  
- **runtime notes:** `allow_delegation=false`; must output numeric score **and** justification tied only to the written requisition (and any recruiter-confirmed Assumptions); must not invent extra must-haves; must not scrape authenticated LinkedIn (example task text already warns this)

**agent:** `communicator`  
- **role:** Candidate Outreach Strategist  
- **goal:** Draft outreach methods and templates for selected candidates  
- **tools:** optional search/scrape for company/public tone; **no send-mail tool**  
- **runtime notes:** templates labeled as drafts; placeholders for recruiter name/company

**agent:** `reporter`  
- **role:** Candidate Reporting Specialist  
- **goal:** Compile the recruiter-facing report  
- **tools:** none (example reporter has no tools)  
- **runtime notes:** `context` = research + match + outreach tasks; output markdown **without** wrapping ```` fences; include an **Assumptions** subsection when the run proceeded on recruiter-confirmed gaps

### Ambiguous, missing, and conflicting inputs

Agents **must not invent a requirement and treat it as decided**. Gaps are either clarified, recorded as labeled Assumptions, or treated as blockers.

**AAMAD / Build personas (Define→Deliver, not the chat crew):**

1. Prefer structured elicitation when the use case is still underspecified.
2. Fill gaps only as labeled **Assumptions** (what the next phase may rely on).
3. Park unresolved items in **Open Questions**.
4. Do not fabricate market facts or product rules without a Source or an Assumption.
5. If `aamad.config.yml` conflicts with this PRD or the SAD, record the conflict under Open Questions and keep **PRD/SAD as scope**.
6. On missing runtime prerequisites, unbound tools, heading mismatches, or guardrail failure: **halt** and write **Diagnostic** — do not continue with a made-up artifact.

**Recruitment runtime crew (chat kickoff):**

| Situation | Required behavior |
|-----------|-------------------|
| Empty title | No `crew.kickoff()` (AC-001, AC-011) |
| Empty must-have skills / requirements | No kickoff; ask recruiter to add must-haves (AC-011) |
| Missing seniority and/or location/remote, or only vague language (e.g. “good culture fit”) | **Clarify-before-kickoff**: list the gaps, ask to add detail **or** explicitly confirm “run anyway” (AC-011) |
| Recruiter confirms run despite gaps | Kickoff allowed; report must list **Assumptions** used (e.g. location unspecified → global public web) (AC-012) |
| Missing contact on a sourced profile | Mark `unverified` / contact unknown; **never** invent email/phone (AC-003) |
| Tool/LLM failure, timeout, unbound tools, guardrail fail | Diagnostic/error; partial results labeled partial; **no silent fill** (AC-008) |
| Hiring outcome | Recommend only; human review; no auto-reject (AC-007) |
| Missing API keys | Fail closed with a clear operator error (NFR-011) |

SAD owns the exact parser/heuristic for “empty must-haves” and “vague-only” detection; the product rule is: **do not silently infer must-haves, seniority, location, or compensation**.

### Kickoff input (from example, productized)

Required interpolated input `job_requirements` including at least:

- title  
- description  
- responsibilities  
- requirements (must-haves)  
- preferred_qualifications (optional)  
- location / remote constraint (product addition; example omitted — **Assumption**)  
- perks_and_benefits (optional)

Chat UI may collect these as one paste (YAML/markdown, as in `main.py`) or a short form that serializes to the same blob.

### Integration Requirements

| Integration | MVP | Deferred |
|-------------|-----|----------|
| LLM provider | Required via env. `LLM_PROVIDER=openai` (default, `OPENAI_API_KEY`, model `gpt-4o`) or `LLM_PROVIDER=grok` (`XAI_API_KEY`, model `grok-4.7`, base URL `https://api.x.ai/v1`). One provider per process. | Additional providers beyond this switch |
| Web search API (`SERPER_API_KEY` or equivalent) | Required | Alternate search vendors |
| Public scrape tool | Allowed on public HTTP pages | Headless login, CAPTCHA solve |
| LinkedIn cookie / Selenium | **Forbidden** | Official LinkedIn API if licensed |
| Email / InMail send | **Forbidden** | Recruiter-OAuth send with confirm |
| ATS (Greenhouse, Ashby, etc.) | Out | Export/webhook |
| Database | Optional run-local files only | Candidate CRM |
| AuthN/Z | Local single operator | SSO, RBAC |

**Security (MVP):** no committed secrets; redact keys from traces; do not persist candidate PII beyond the run artifact unless the operator exports; recommend-only UX copy.

**Performance targets:** see NFR section.

### Infrastructure Specifications

- Hosting: local/dev compose or single backend process + static frontend (SAD).  
- Compute: CPU; no GPU. Memory sized for one concurrent crew unless SAD states otherwise.  
- Network: outbound HTTPS to LLM and search/scrape; deny arbitrary credentialed sites.  
- Monitoring: health endpoint; log run id, task lifecycle, errors, token/search counts; redact secrets. Framework traces under `logs` during Build.  
- CI: lint, test, build only; no live deploy without operator authorization.

---

## 4. Functional Requirements

### Core Features (Priority P0)

**P0-1 Job requirement intake**  
*As a recruiter, I want to submit a structured job requirement in chat (or paste the example YAML-style blob) so the crew knows what to search for.*  
**Acceptance (AC-001):** Given a title + must-have skills, When I submit, Then the backend stores/forwards a single `job_requirements` payload and does not kick off on empty title.  
**Constraints:** English; max length to be capped in SAD (prevent context overflow).

**P0-2 Sequential crew kickoff**  
*As a recruiter, I want one action to run research → match → outreach draft → report so I do not orchestrate agents myself.*  
**Acceptance (AC-002):** Given valid input, When kickoff succeeds, Then all four tasks run in order and the report task receives the three prior outputs as context.  
**Trace:** CrewAI example `crew.py`.

**P0-3 Public candidate research**  
*As a recruiter, I want up to N public candidate leads (default N=10, configurable 5–10) with source URLs.*  
**Acceptance (AC-003):** Each listed candidate includes name (or public handle), evidence summary, and `source_url`, **or** is explicitly marked `unverified` / omitted. Invented emails/phones are defects.  
**Forbidden:** LinkedIn cookie, `LI_AT`, Selenium login.

**P0-4 Match and score**  
*As a recruiter, I want a ranked list with numeric scores and justifications tied to must-have vs nice-to-have skills.*  
**Acceptance (AC-004):** Report includes ranked candidates, score, and written justification referencing job requirements; protected-class attributes are not used as score features (no photos, no inferred ethnicity/age/gender).

**P0-5 Outreach drafts (no send)**  
*As a recruiter, I want copy-ready templates I can paste into my own mail/LinkedIn.*  
**Acceptance (AC-005):** Templates exist for top candidates; UI/report states they were **not sent**; no send API is called.

**P0-6 Recruiter report**  
*As a recruiter, I want one markdown report with profiles, scores, outreach, and sources.*  
**Acceptance (AC-006):** Report is markdown without wrapping code fences; includes recommendations; available in the chat transcript and copy/download.

**P0-7 Human-in-the-loop framing**  
*As a recruiter, I want the system to recommend, not decide.*  
**Acceptance (AC-007):** UI copy states recommendations require human review; no reject/advance-candidate API; no “not qualified” auto-notice to people.

**P0-8 Run status and errors**  
*As a recruiter, I want to know if search/LLM failed instead of a fake shortlist.*  
**Acceptance (AC-008):** On tool/LLM failure, Diagnostic/error is shown; partial results labeled partial; no silent fill.

**P0-9 Secrets via environment**  
*As an operator, I want keys in env only.*  
**Acceptance (AC-009):** `.env.example` lists `OPENAI_API_KEY` when the provider is OpenAI, `XAI_API_KEY` (alias `GROK_API_KEY`) when the provider is Grok, and `SERPER_API_KEY`; **does not** require `LINKEDIN_COOKIE`. No secret values in repo or Prompt Trace. The active provider is `LLM_PROVIDER` (`openai` or `grok`).

**P0-10 Chat MVP UI**  
*As a recruiter, I want a minimal chat surface to submit a req and read the report.*  
**Acceptance (AC-010):** Happy path completable in the web UI; empty, in-progress, **needs-clarification**, error, and completed states exist. Theme: system; visual style: minimal (example config).

**P0-11 Ambiguous or missing job requirements**  
*As a recruiter, I want the assistant to ask for missing critical fields (or confirm Assumptions) instead of inventing a job spec and sourcing against it.*  
**Acceptance (AC-011):** Given a submit with empty title, empty must-have skills, or only vague criteria without seniority **and** without location/remote, When I send the req, Then the system **does not** call `crew.kickoff()`, And the chat lists the specific gaps, And it asks me to add detail or confirm “run anyway” where that path is allowed (not allowed for empty title or empty must-haves).  
**Acceptance (AC-012):** Given I confirm “run anyway” on allowed gaps (missing seniority and/or location/remote), When the crew finishes, Then the recruiter report includes an **Assumptions** subsection stating each inferred or omitted constraint, And matcher justifications cite those Assumptions rather than invented must-haves.  
**Acceptance (AC-013):** Given missing/ambiguous inputs on AAMAD artifacts or runtime prerequisites, When a persona or crew cannot proceed safely, Then it writes Assumptions and Open Questions and/or a **Diagnostic** and **halts**; it does not fabricate candidates, contacts, scores-as-decisions, or undocumented requirements.

### Enhanced Features (Priority P1)

- Adjustable N and location/remote filter in the form (if not in P0 paste).  
- Persist last N reports locally for the operator.  
- Stream task-level progress messages.  
- Export PDF (nice-to-have; markdown download is P0).

### Future Features (Priority P2 / Future Work)

- Official people-search or job-board APIs.  
- ATS export/webhooks.  
- Recruiter-OAuth send with explicit confirm.  
- Multi-user auth, SSO, RBAC.  
- Bias-audit packs / NYC AEDT / EU high-risk conformity.  
- Job-seeker reverse matching (CrewAI match_profile_to_positions).  
- Hierarchical crew, memory, or `kickoff_for_each` batch reqs.  
- Interview scheduling, video, assessments, onboarding.  
- Emotion/personality inference (**never** — prohibited direction).

---

## 5. Non-Functional Requirements

### Performance Requirements

| ID | Requirement |
|----|-------------|
| NFR-001 | P95 kickoff completion for default N≤10: target **≤ 8 minutes** on a configured LLM; if exceeded, timed Diagnostic (SAD may tighten). |
| NFR-002 | Chat UI acknowledges submit **≤ 2 seconds** (run continues asynchronously or with progress). |
| NFR-003 | MVP concurrency: **1 active crew** per process unless SAD raises it. |
| NFR-004 | Availability: best-effort local/dev; no 99.9% SLA in MVP. |

### Security & Compliance

| ID | Requirement |
|----|-------------|
| NFR-005 | No secrets in git, artifacts, or traces. |
| NFR-006 | Assistive use only; not a solely automated employment decision (GDPR Art. 22; EU AI Act Annex III awareness). |
| NFR-007 | Minimize PII: no durable shared candidate database in MVP. |
| NFR-008 | Security assessment before Deliver when config requires it (`security.require_security_assessment: true` in example config). |
| NFR-009 | Dependency audit on Build/Deliver path. |
| NFR-010 | Scraping limited to publicly accessible pages; robots/ToS: no authenticated LinkedIn. |

### Scalability & Reliability

| ID | Requirement |
|----|-------------|
| NFR-011 | Fail closed on missing API keys (clear operator error). |
| NFR-012 | Retries per adapter (`max_retry_limit >= 2`); then halt with Diagnostic. |
| NFR-013 | Scale-out, multi-tenant, and queueing are **deferred**. |
| NFR-014 | Idempotent display of a completed run id (no duplicate silent sends — sends do not exist). |

### Usability

| ID | Requirement |
|----|-------------|
| NFR-015 | Keyboard-usable chat compose/send. |
| NFR-016 | WCAG AA as stretch; MVP: readable contrast, visible errors (SAD/FE). |
| NFR-017 | Coding standards from example config: type checking true; max file lines 400. |

---

## 6. User Experience Design

### Interface Requirements

- Single-page chat (AAMAD frontend epic): history, composer, send.  
- Optional structured fields may collapse into the first user message.  
- Desktop-first; mobile readable but not a native app.  
- `ui.theme: system`, `visual_style: minimal`, `prefer_modals: false` (example config).  
- Future-work features must be visibly labeled if shown.

### Agent Interaction Design

- Show which task is running (researcher / matcher / communicator / reporter).  
- **Needs-clarification** is a first-class chat state: list gaps as questions; do not start the four-agent pipeline until the recruiter answers or confirms an allowed “run anyway.”  
- Final assistant message **is** the report (or a summary + download), including Assumptions when the run used confirmed gaps.  
- Errors: missing key, timeout, zero public hits, scrape blocked, guardrail/prerequisite Diagnostic.  
- Transparency: scores + justifications + URLs; model name may be shown; keys never shown.  
- Language: “recommended for recruiter review,” never “rejected by AI.”  
- Matcher scores only against the written requisition plus recruiter-confirmed Assumptions; culture-fit-only language is not treated as a scored must-have.

---

## 7. Success Metrics & KPIs

### Business / Operational

| KPI | MVP target |
|-----|------------|
| Recruiter time saved (hours per week) | **≥ 3 hours/week** per active recruiter (see measurement below) |
| Recruiter time saved (hours per requisition, first-pass) | **≥ 2 hours/req** vs that recruiter’s baseline for the same first-pass work |
| Time-to-shortlist (paste → report) | < 8 minutes typical (NFR-001) |
| Recruiter usefulness (qualitative) | Operator can use ≥1 lead or template from a golden req |
| Auto-contact incidents | 0 |
| LinkedIn cookie usage | 0 |

**Hours-per-week measurement (required for this KPI):**

- **Scope of time:** first-pass **sourcing + scoring/shortlist judgment + outreach drafting only**. Exclude interviewing, offer, scheduling, and ATS admin unless later expanded.
- **Active recruiter:** completed **≥ 1** successful kickoff in the measurement week (clarify-only sessions do not count as saved time).
- **Formula:**  
  `hours_saved_per_week = H_baseline_week − H_with_assistant_week`  
  where `H_with_assistant_week` = (sum of tool wait/review minutes ÷ 60) + remaining manual first-pass minutes for those reqs.
- **Baseline (`H_baseline_week`):** recruiter diary or estimated hours for the same first-pass work **before** the assistant, averaged over **2 consecutive weeks**, then compared to **2 weeks** with the assistant. If no diary exists, use a one-time self-report of hours/week on that work, labeled estimate.
- **Per-req check:** `hours_saved_per_req = h_baseline_first_pass − (kickoff_duration + review_duration)`; roll up: `hours_saved_per_week ≈ hours_saved_per_req × reqs_completed_that_week`.
- **QA vs ops:** unit/integration tests do **not** assert hours/week. Operator (or QA manual protocol) records the diary after a usable MVP; `@qa.eng` may add a checklist item that the metric is defined and a capture method exists (spreadsheet or form), not that the 3-hour target is hit in CI.

The 3 hours/week and 2 hours/req targets are **Assumptions** derived from the MRD directional range (about 4–8 hours of first-pass work per requisition). They are not SHRM cost-per-hire conversions. Do not claim quality-of-hire lift from this KPI.

### Technical

| KPI | MVP target |
|-----|------------|
| Kickoff success on fixture req | 100% in QA happy path with stubbed/search-mocked tests as designed by QA |
| Candidates with `source_url` | 100% of non-unverified rows |
| Crew YAML load | 100% agents/tasks bind before kickoff |
| Unit + integration tests | Required (`testing.require_unit_tests` / `require_integration_tests` in example config); map to AC IDs |

### User Experience

| KPI | MVP target |
|-----|------------|
| Task completion (submit → report, needs-clarification, or explicit error) | 100% of sessions reach a terminal state |
| Empty/error/ambiguity understandability | QA checklist: user can retry or clarify without restarting the stack |
| Silent kickoff on empty title or empty must-haves | 0 |

Quality-of-hire and offer-accept rates are **not** MVP KPIs (no closed-loop hiring data). Recruiter time saved **is** an MVP operational KPI; it is measured after operators use the assistant, not in automated tests.

---

## 8. Implementation Strategy

### Development Phases

- **Phase 1 (Define):** this MRD + PRD; SAD/SFS via `@system.arch`; optional user stories via `*create-stories`.  
- **Phase 2 (Build):** `@project.mgr` setup → FE/BE (may parallel) → `@integration.eng` → `@qa.eng` (`*test-unit`, `*test-integration`, `*qa`) → `@security.eng`. Honor CrewAI adapter. Personas encountering ambiguous PRD/SAD inputs record **Assumptions** and **Open Questions** and do not invent scope; on missing prerequisites they **Halt and Report** / Diagnostic.  
- **Phase 3 (Deliver):** `@devops.eng` configs + runbook + user guide; **no live deploy** without explicit operator authorization.

### Resource Requirements

AAMAD personas only; Python backend; minimal web frontend. LLM and Serper accounts required to run non-mocked e2e. No dedicated data-science team.

### Risk Mitigation

| Risk | Plan |
|------|------|
| ToS / scraping | P0 forbid LinkedIn cookies |
| Hallucination | AC-003; QA fixtures |
| Budget | caps in SAD; smaller N |
| Scope creep to ATS | P2 list |
| Missing `aamad.config.yml` | honor example; Open Question to copy file |
| Ambiguous job req / invented spec | P0-11; AC-011–AC-013; no kickoff on empty title or empty must-haves |

---

## 9. Launch & Go-to-Market Strategy

**N/A for commercial launch in this cycle.** Immediate “launch” is a **local/demo MVP** for the operator. No pricing, sales motion, or public marketing plan. Revisit after a successful QA+security gate if the operator wants commercialization (MRD §5).

---

## Quality Assurance Checklist

- [x] Requirements traceable to MRD and CrewAI recruitment example (or Assumptions)  
- [x] Technical specs feasible with CrewAI adapter  
- [x] Success metrics aligned with assistive-shortlist objectives  
- [x] MVP vs Future Work explicit  
- [x] Market sections included (MRD was not skipped)  
- [x] Terminal headings Sources / Assumptions / Open Questions / Audit  

---

## Sources

1. `project-context/1.define/mrd.md` (create-mrd, 2026-10-13).  
2. CrewAI recruitment example: `agents.yaml`, `tasks.yaml`, `crew.py`, `main.py`, README, `.env.example` — https://github.com/crewAIInc/crewAI-examples/tree/main/crews/recruitment — retrieved 2026-10-13.  
3. Stakeholder request: `@product-mgr` `*create-mrd` then `*create-prd` for a recruitment assistant based on that example — 2026-10-13.  
4. `.cursor/templates/prd-template.md`, `.cursor/agents/product-mgr.md`, `.cursor/rules/adapter-crewai.mdc`, `.cursor/rules/aamad-core.mdc`.  
5. `aamad.config.example.yml` (no project `aamad.config.yml`).  
6. SHRM 2025 recruiting benchmarks; LinkedIn Future of Recruiting 2025; EU AI Act Annex III; GDPR Art. 22 — as cited in the MRD.  
7. Stakeholder: document ambiguous-requirement behavior in this PRD (clarify-before-kickoff, Assumptions/Open Questions, Diagnostic halt) — 2026-10-16.  
8. `.cursor/rules/aamad-core.mdc` (missing/ambiguous inputs → Assumptions and Open Questions; do not fabricate); `.cursor/rules/adapter-crewai.mdc` (halt + Diagnostic on missing prerequisites / guardrail failure).  
9. Stakeholder: add success metrics for recruiter time savings in hours per week — 2026-10-16.  
10. MRD business case: directional 4–8 hours per requisition on first-pass sourcing and outreach drafting (not a surveyed baseline).

---

## Assumptions

- MRD was produced (not skipped); market sections in this PRD are summaries of that MRD.  
- Elicitation/`system-description.md` skipped because the CrewAI example plus stakeholder command sufficiently specified the use case.  
- `AAMAD_TARGET_RUNTIME` unset → **`crewai`**.  
- Example config preferences apply until an `aamad.config.yml` exists.  
- Location/remote is a product field even though the example `main.py` job blob omitted it.  
- Default N=10 follows the example; operator may lower to 5 for cost (Open Question in MRD).  
- LLM provider is selected by `LLM_PROVIDER`: `openai` (default, `OPENAI_MODEL` default `gpt-4o`) or `grok` (`GROK_MODEL` default `grok-4.7`, xAI base URL `https://api.x.ai/v1`). Operator request 2026-10-21. Only the selected provider’s key is required.  
- Launch/GTM is N/A (internal/demo delivery).  
- Python is the backend language.  
- Scoring rubric details (weights) are SAD-owned if not specified here: skills match, seniority, evidence quality, location/remote fit; **not** demographic proxies.  
- “Run anyway” is allowed only for missing seniority and/or location/remote (and similarly non-critical gaps SAD lists); empty title and empty must-haves remain hard blocks.  
- Vague phrases such as “good culture fit” are not scored must-haves unless the recruiter writes observable criteria.  
- Recruiter time-saved targets (**≥ 3 hours/week**, **≥ 2 hours/req** on first-pass work) assume an active recruiter who previously spent on the order of **4–8 hours/req** on sourcing/scoring/outreach drafting (MRD directional case) and completes enough kickoffs that weekly roll-up can reach 3 hours. They are product goals, not measured baselines.  
- Time-saved hours count only first-pass work in scope; they are not a reduction in SHRM “days to screen” calendar time.

---

## Open Questions

1. Pin default model and temperature (example GPT-4o vs cheaper) — `@system.arch` / operator.  
2. Default N=10 vs 5.  
3. Copy `aamad.config.yml` before Build?  
4. Any allowed people-data API besides Serper+public pages?  
5. Single local operator vs basic auth?  
6. Must the chat stream tokens, or is batched report enough for MVP? (P1 stream vs P0 batch.)  
7. User stories (`*create-stories`) before SAD, or SAD next?  
8. Jurisdiction banner in UI (US vs EU)?  
9. Exact NLP/heuristic for “vague-only” reqs (beyond empty title / empty must-haves) — `@system.arch`.  
10. Should “run anyway” require a typed confirmation phrase vs a single chat reply?  
11. Operator-approved method for the hours/week diary (spreadsheet vs in-app prompt) before first measurement window?  
12. Is ≥ 3 hours/week the right bar if typical load is « 1 req/week (use per-req 2 hours as the binding KPI in that case)?  

---

## Audit

- **timestamp:** 2026-10-16T03:15:00Z  
- **persona id:** `product-mgr`  
- **action:** `create-prd` (update: recruiter time-saved KPIs in hours/week and hours/req)  
- AAMAD_TARGET_RUNTIME: crewai  
- **llm / temperature / max_tokens:** N/A for this artifact  
- **Prompt Trace:** omitted — KPI update from stakeholder + MRD directional first-pass hours, not a production agent prompt  
- **tools:** edit `prd.md`  
- **handoff:** `@system.arch` / `@qa.eng` — time-saved is operational (diary), not a CI assertion; optional in-app capture is Open Question 11
- **revision:** 2026-10-21 — operator request: `LLM_PROVIDER` switches the crew between OpenAI and Grok (xAI). Persona `backend-eng`.  

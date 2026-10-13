# Market Research Document — Recruitment Assistant

**Primary Focus**: Multi-agent recruitment assistant that sources, scores, and recommends candidates from a job requisition, then drafts outreach strategy and a recruiter-facing report.  
**System Concept**: Production-oriented MVP of the CrewAI “AI Crew for Recruitment” pattern (researcher → matcher → communicator → reporter), delivered as a chat-driven operator tool rather than a CLI-only demo.  
**Selected Runtime** (implementation choice for the generated MVP, not the AAMAD methodology): `crewai`

---

## Executive Summary

**Market Opportunity.** Dedicated recruitment software is a multi-billion-dollar category with mid-single to high-single-digit CAGRs depending on analyst scope: Mordor Intelligence places the market at USD 3.61 billion in 2025 and USD 3.77 billion in 2026, reaching USD 5.5 billion by 2031 (7.85% CAGR 2026–2031). Broader talent-acquisition software is larger (USD 10.37 billion in 2025; USD 10.95 billion in 2026). A narrower “AI recruitment software” slice is smaller but already material (USD 596 million in 2025; USD 641 million in 2026; USD 921 million by 2031). Independently, Grand View Research (via secondary summaries) sizes a wider “AI in recruitment” spend at USD 8.16 billion in 2025 growing at ~25% CAGR through 2030 — a definitional conflict that this MRD treats as **scope difference**, not a single TAM. Talent teams still spend significant time on screening (SHRM: 8–9 days each for screening and interviewing; median time-to-fill about 1.5 months). LinkedIn reports 37% of organizations actively integrating or experimenting with generative AI in recruiting (up from 27% year over year). The business case for an **assistive, explainable, human-supervised** sourcing-and-shortlist copilot is therefore real: reduce days-to-shortlist and recruiter busywork without replacing ATS systems of record.

**Technical Feasibility.** The CrewAI recruitment example already demonstrates a sequential four-agent crew with YAML-declared roles and tasks, Serper web search, website scrape, optional LinkedIn tooling, and a markdown recruiter report. That pattern maps cleanly to AAMAD’s CrewAI adapter (externalized `config/agents.yaml` and `config/tasks.yaml`, `Task.context` chaining, `allow_delegation=false`, sequential process). Feasibility for an MVP is **high** if the product **does not** copy the example’s LinkedIn cookie/Selenium path (the example itself disclaims ToS risk and account bans). Success probability for a local/chat MVP with public-web research, scored shortlists, outreach templates, and human review is high. Success probability for a production ATS replacement, bulk outreach sender, or legally automated hiring decision engine is low in this phase and should be deferred.

**Recommended Approach.** Position the MVP as an **operator copilot for technical/professional requisitions**: ingest a structured job requirement, run a sequential crew, return a cited shortlist with scores/justifications plus outreach drafts, and require a recruiter to accept or reject recommendations. Do not scrape authenticated LinkedIn, do not auto-send mail, and do not auto-reject candidates. Treat scoring as decision-support under human oversight (EU AI Act Annex III employment systems; GDPR automated-decision constraints). Use `crewai` as the Phase 2 runtime because the reference use case is already CrewAI YAML-first sequential orchestration. Compete on **transparency of match rationale, reproducible crew config, and ToS-safe sourcing**, not on ATS feature breadth or LinkedIn graph access.

---

## Detailed Findings by Dimension

### 1. Market Analysis & Opportunity Assessment

#### Key Insights

1. **Hiring software spend is growing, but TAM figures conflict by definition.** Recruitment *software* (ATS + adjacent recruiting apps) is ~USD 2.5–3.8 billion in 2025–2026 across IMARC, TBRC, Coherent, and Mordor. Talent *acquisition* suites are ~USD 10–11 billion. Dedicated AI recruiting platforms are sub-USD 1 billion today. Broader “AI in HR/recruiting” narratives quote several billion more. Product strategy should target the **AI sourcing/shortlist copilot** wedge inside recruiting software, not the full HCM suite.
2. **ATS remains the system of record; analytics and copilots are the growth story.** Applicant-tracking still held 53.87% of recruitment-software functionality spend in 2025 (Mordor); talent-analytics is the fastest functionality CAGR (9.82%). Buyers want copilots *on top of* ATS, not greenfield replacements — a gap this assistant can occupy if it stays integration-light for MVP and ATS-export-friendly later.
3. **SME growth outpaces large-enterprise share.** Large enterprises held 60.95% of 2025 spend, but SMEs are forecast at 10.23% CAGR. A lightweight chat MVP with API-key LLM usage (no enterprise ATS rollout) is a plausible SME / startup TA wedge; enterprise deals will require connectors, SSO, and audit logs (Future Work).
4. **Recruiter economics justify assistive automation.** SHRM 2025: recruiting is ~26% of HR budget on average; nonexecutive cost-per-hire USD 5,475; executive USD 35,879; screening and interviewing each average 8–9 days. SmartRecruiters 2025 claims organizations using AI hire ~26% faster (vendor research; treat as directional). Time saved on *research + first-pass scoring + first-touch copy* is the ROI locus for this product.
5. **GenAI adoption in TA is past early curiosity but not yet default.** LinkedIn Future of Recruiting 2025: 37% actively integrating or experimenting with gen AI (from 27%). The remaining majority is a conversion market if tools are explainable, cheap to try, and do not violate platform ToS.

#### Data Points

| Metric | Value | Source / date |
|--------|--------|----------------|
| Recruitment software market | USD 3.61B (2025), USD 3.77B (2026), USD 5.5B (2031), 7.85% CAGR | Mordor Intelligence, retrieved 2026-10-13 |
| Cloud share of recruitment software | 68.73% (2025); cloud CAGR 9.21% to 2031 | Mordor Intelligence |
| ATS share of functionality | 53.87% (2025) | Mordor Intelligence |
| Talent acquisition software | USD 10.37B (2025), USD 10.95B (2026), USD 14.4B (2031), 5.63% CAGR | Mordor Intelligence |
| AI recruitment software (narrow) | USD 596.16M (2025), USD 640.99M (2026), USD 920.91M (2031), 7.52% CAGR | Mordor Intelligence AI Recruitment |
| AI in recruitment (broad) | USD 8.16B (2025) → USD 15.24B (2030), 24.8% CAGR | Grand View Research as summarized by Pin, 2026 report page |
| TBRC recruitment software | USD 2.54B (2025) → USD 2.78B (2026), 9.5% historic CAGR | The Business Research Company / GII, 2026 |
| IMARC recruitment software | USD 2.5B (2025) → USD 3.9B (2034), 4.80% CAGR | IMARC Group |
| Coherent recruitment software | USD 3.30B (2025) → USD 6.20B (2032), 9.4% CAGR | Coherent Market Insights |
| North America share | 34.62% of 2025 recruitment software revenue | Mordor Intelligence |
| GenAI in recruiting | 37% orgs integrating/experimenting (was 27%) | LinkedIn Future of Recruiting 2025 |
| Nonexecutive / executive CPH | USD 5,475 / USD 35,879 | SHRM 2025 Recruiting benchmarking |
| Median time-to-fill | ~1.5 months exec and non-exec | SHRM 2025 |
| AI-using firms time-to-hire | ~26% faster (vendor claim) | SmartRecruiters Recruitment Benchmarks 2025 |

**Conflicting information:** TBRC/IMARC 2025 sizes (~USD 2.5B) sit below Mordor/Coherent (~USD 3.3–3.6B). Grand View “AI in recruitment” is an order of magnitude above Mordor’s dedicated AI recruiting software. Implication: do not quote a single TAM in investor-facing copy without stating the definition.

#### Target Audience (personas)

| Persona | Setting | Pain | Willingness to pay (inferred) |
|---------|---------|------|-------------------------------|
| **Agency / in-house recruiter (primary)** | 5–50 reqs; technical or professional roles | Manual Boolean search, inconsistent scoring, slow first-touch copy | Tool budget if it cuts hours per req; seats cheaper than LinkedIn Recruiter |
| **Hiring manager (secondary)** | Reviews shortlists, not power-user of ATS | Opaque “here are 10 people” without rationale | Indirect; values explainable scores |
| **TA operations / people-tech (buyer, later)** | Governance, bias, logs | Shadow-IT copilots, ToS risk, unaudited LLMs | Pays for compliance and audit; MVP is too thin |

#### Competitive Landscape (feature view)

| Competitor / alternative | Type | Strength | Gap vs this assistant |
|--------------------------|------|----------|------------------------|
| LinkedIn Recruiter | Sourcing network | Graph, InMail, brand | Cost, single-network lock-in, limited multi-agent workflow |
| Greenhouse, Lever, Ashby, iCIMS, SmartRecruiters | ATS / TA workflow | Pipeline, structured hiring, integrations | Weak autonomous *research* crew; not YAML-reproducible agent graphs |
| Workday / SAP / Oracle HCM | Enterprise suite | System of record, emerging “agents” | Heavy; not a lightweight crew MVP |
| Eightfold, Phenom, SeekOut, Gem, Juicebox/PeopleGPT | AI matching / CRM / sourcing | Scale data, sequencing | Closed models; little open crew inspectability |
| DIY ChatGPT + search | Informal | Cheap | No task graph, no scored report contract, weak audit |
| CrewAI recruitment example (reference, not competitor) | Open example | Exact workflow | CLI-only; LinkedIn cookie tool is ToS-unsafe; no product UI/ops |

**Market gaps this product can claim (MVP):** (1) inspectable multi-agent pipeline for source → score → outreach-draft → report; (2) human-gated recommendations with written justifications; (3) ToS-safe public-web research instead of authenticated scraping; (4) chat UI over a reproducible YAML crew.

#### Business Case (directional)

If a recruiter spends even 4–8 hours per requisition on first-pass sourcing and outreach drafting, and SHRM nonexecutive CPH is USD 5,475, shaving one day of cycle time and a few hours of recruiter time per req is the MVP ROI story. Do **not** claim quality-of-hire lift without measured A/B data (Open Question).

#### Implications

MVP should be a **copilot beside ATS**, not an ATS. Primary ICP: technical/professional hiring by small TA teams. Pricing (if ever commercialized) is seat + LLM usage, not enterprise HCM. Differentiation is workflow transparency, not candidate-graph scale.

---

### 2. Technical Feasibility & Requirements Analysis

#### Key Insights

1. **The reference architecture is already a sequential CrewAI crew.** Official example agents: Job Candidate Researcher, Candidate Matcher and Scorer, Candidate Outreach Strategist, Candidate Reporting Specialist. Tasks: research 10 candidates → rank/score with justifications → outreach methods/templates → markdown recruiter report. Reporter task uses explicit `context` from the prior three tasks. Process is `Process.sequential`; all agents `allow_delegation=False`.
2. **Tooling must be least-privilege and legally constrained.** Example binds SerperDevTool + ScrapeWebsiteTool to researcher/matcher/communicator; LinkedInTool + cookie `LINKEDIN_COOKIE` to researcher only; reporter has no tools. README **explicitly** warns that cookie auth to LinkedIn is a Selenium demo and may violate LinkedIn ToS. **Product implication: MVP must omit authenticated LinkedIn scraping.** Public search + allowed public pages only.
3. **CrewAI adapter fit is strong.** AAMAD CrewAI rules require YAML agents/tasks, sequential default, `max_iter <= 12` unless justified, `max_retry_limit >= 2`, `max_rpm` at crew level, `memory=False` default, secrets via env (`.env.example` names only). The example already matches YAML-first sequential style; Build phase should add iteration/time/RPM caps the demo lacks.
4. **Integrations for MVP are few.** Required: LLM provider key, Serper (or equivalent search) key, optional scrape. Not required: ATS APIs, email senders, calendars, HRIS. Storage can be run-scoped artifacts (report markdown) plus optional local persistence — no candidate PII warehouse in MVP.
5. **Technical risks are sourcing quality, hallucination, cost, and compliance — not “can we run a crew.”** Web search will miss private profiles; LLMs may invent contact data; GPT-4-class runs are non-trivial cost per kickoff; scoring without a documented rubric is a bias/legal risk.

#### Data Points / runtime notes

- Example default model: GPT-4o (README); env names: `OPENAI_API_KEY`, `SERPER_API_KEY`, `LINKEDIN_COOKIE`.
- Example input: a single `job_requirements` blob (title, description, responsibilities, requirements, preferred qualifications, perks).
- Example expected research output: **10** candidates with contact info and brief profiles.
- CrewAI also publishes a related “Match Profile to Positions” (CV → jobs) example; **this product is the employer-side reverse** (job → candidates), not the job-seeker matcher, unless later expanded.

#### Agent architecture pattern (recommended)

Sequential pipeline with deterministic context merge at the report task — a proven pattern for research-then-synthesize crews. Hierarchical manager/delegation is **not** justified for MVP (adapter: prefer sequential; example uses no delegation).

#### Scalability

Bottlenecks: LLM tokens and search API RPM, not HTTP concurrency. Scale strategy: one kickoff per requisition, `max_rpm`, no `kickoff_for_each` unless independent reqs. Horizontal scale is Future Work.

#### Infrastructure / cost (order of magnitude, assumed)

Local or single-container Python service + static/chat UI; LLM + Serper billed per run. No GPU requirement. Enterprise multi-tenant, VPC, and SSO are out of MVP.

#### Implications

Build a CrewAI YAML crew + chat kickoff API + markdown/chat report. Ban LinkedIn cookie tools in product requirements. Add structured score rubric and “unknown contact” rather than fabricated emails.

---

### 3. User Experience & Workflow Analysis

#### Key Insights

1. **User journey (operator).** Recruiter pastes or structures a job requirement → confirms start → waits with progress/status → reads ranked candidates, scores, evidence, and outreach drafts → copies or exports report → (human) performs actual outreach in their email/LinkedIn. Optional later: iterate (“more backend-heavy candidates”).
2. **Interface.** AAMAD MVP UI is a chat/operator surface, not a full ATS board. Requirements: job-req composer or first message, run status, streamed or batched assistant report, error/empty-result states, copy/download of markdown report. Visual style per example config: minimal, system theme.
3. **Automation vs HITL.** Fully automatable: web research, rubric scoring, template drafting, report compilation. **Must remain human:** candidate contact, legal assessment, offer/reject, any action that affects a natural person’s access to employment. Scores are recommendations, not decisions.
4. **Adoption barriers.** Fear of hallucinated candidates; LinkedIn ToS scare from the upstream example; “black box” ranking; extra tool besides ATS. Enablers: citations/URLs, explicit “unverified contact” flags, visible agent steps, no auto-send.
5. **Success metrics (product).** Time from job paste to usable shortlist; % of listed candidates with a real public URL; recruiter rating of shortlist usefulness; LLM/search cost per run; zero auto-send incidents.

#### User journey (happy path)

1. Recruiter submits job requirements (title, must-haves, location/remote, seniority).
2. Researcher gathers up to N public candidate profiles (default N=10 in the example; MVP may allow 5–10 for cost).
3. Matcher scores against a transparent rubric (skills, seniority, domain, evidence quality).
4. Communicator drafts channel-appropriate outreach (email/LinkedIn *templates only*).
5. Reporter emits a single markdown report without code fences, as in the example `expected_output`.
6. Recruiter reviews, edits, and acts outside the system.

#### Implications

Chat UI + structured first turn. Show agent/task progress. Never present scores as pass/fail hiring decisions. Empty and low-confidence states must be first-class.

---

### 4. Production & Operations Requirements

#### Key Insights

1. **Deployment.** Smallest MVP: local compose or single backend + static frontend, health endpoint, env-based secrets. Align with SAD DevOps later; do not live-deploy without operator authorization (AAMAD Deliver policy).
2. **Observability.** Prompt Trace and Trace Log under `project-context/2.build/logs` for the *framework* build; application should log task start/stop, retries, token/search usage, **redacted** of secrets and raw cookies. Recruiter-facing: run id, duration, model name (not keys).
3. **Security & compliance.** Candidate data is personal data. Minimize retention (session/run artifacts). No committed secrets. EU AI Act Annex III(4)(a) lists AI for recruitment/selection (ads, filtering, evaluating candidates) as high-risk when in scope; Article 6(3) does not exempt profiling. GDPR Art. 22 constrains solely automated decisions with legal/similarly significant effect — **do not auto-decide hire/reject**. NYC Local Law 144 (and similar) can require bias audits for automated employment decision tools used on NYC candidates — **out of MVP certification**, but the product must remain assistive. Emotion inference in workplace contexts is restricted under the AI Act prohibited-practices regime — do not add “personality/emotion” scoring.
4. **Maintenance.** Pin CrewAI and tool versions; treat YAML as the product contract; `aamad` docs sync after code drift.
5. **Cost structure.** Dev: AAMAD Define/Build/Deliver. Run: LLM + Serper per kickoff (dominant). Ops: logs/storage small. No VC-scale data-acquisition budget.
6. **Continuity.** Idempotent kickoff per run id; on LLM/search failure, return Diagnostic to operator, do not silently invent a shortlist.

#### Implications

`.env.example` with `OPENAI_API_KEY` (or provider-neutral names), `SERPER_API_KEY`; **no** `LINKEDIN_COOKIE` in product. Retention = run-local. Security assessment recommended before Deliver (`aamad.config.example.yml` sets `security.require_security_assessment: true`; project has no `aamad.config.yml` yet).

---

### 5. Innovation & Differentiation Analysis

#### Key Insights

1. **UVP.** An inspectable four-agent recruitment crew with written score justifications and ToS-safe sourcing, wrapped in a recruiter chat — vs closed sourcing suites and vs the unsafe LinkedIn-cookie demo.
2. **Emerging tech.** Agentic ATS copilots (Mordor cites Workday/Paradox-class moves) validate the category; this project should stay **open, small, and explainable** rather than chase conversational scheduling.
3. **IP.** No patent clearance was performed. Using CrewAI examples (MIT-licensed example repo) as *inspiration* is fine; do not copy LinkedIn cookie scraping into a product. Record third-party notices at Deliver if required.
4. **Trends.** Skills-based hiring, explainable ranking, bias scrutiny, and buyer fatigue with overlapping point tools. Long-term viability depends on staying a **focused copilot** or later attaching to ATS APIs — not becoming a sixth ATS.
5. **Partnerships (later).** Official job-board/search APIs; ATS webhooks (Greenhouse/Ashby); email via recruiter-owned Gmail/Outlook — never platform scraping.
6. **Monetization.** Internal/demo MVP first. If commercial: usage-based LLM pass-through + seat. Not in MVP scope to pick a price.

#### Implications

Differentiate on **process transparency + legal hygiene**. Future: official APIs, bias-monitoring, ATS export. Not in MVP: autonomous outreach, personality inference, LinkedIn graph.

---

## Critical Decision Points

### Go / No-Go Factors

| Factor | Go condition |
|--------|----------------|
| Legal sourcing | No authenticated LinkedIn/Selenium cookie usage in the product |
| Human oversight | Scores and reports never auto-reject or auto-contact candidates |
| Reference fidelity | Four-agent sequential pipeline preserved from the CrewAI example |
| Runtime | CrewAI YAML crew executable via `kickoff` with env secrets |
| MVP UI | Recruiter can submit a job req and read a report in chat |
| Evidence | Candidates include source URLs; fabricated contacts are forbidden |

**No-Go (for this MVP):** replacing ATS; sending email/InMail; storing a durable candidate CRM; claiming EU high-risk conformity; using LinkedIn cookies.

### Technical Architecture Choices

- **Runtime:** `crewai` (default AAMAD adapter; matches the example).
- **Process:** sequential; `allow_delegation=false`; `memory=false`.
- **Tools:** Serper (or equivalent) + public scrape; reporter has no search tools.
- **Language:** Python (example config / AAMAD example).
- **UI:** minimal chat (AAMAD frontend epic).
- **Auth (MVP):** none or single-operator local; no SSO.

### Market Positioning

**Assistive shortlist copilot for technical/professional requisitions**, for recruiters and hiring managers in SMEs/startups, North America/Europe first (English job reqs). Not a LinkedIn Recruiter replacement.

### Resource Requirements (MVP)

Single squad following AAMAD: Product (this phase) → Architect → Setup/FE/BE/Integration/QA/Security → DevOps configs. Timeline is one Define + one Build + one Deliver cycle, not a 12-month product org. Budget is LLM/search usage plus engineering time. Formal market spend / GTM team is N/A until commercialization.

---

## Risk Assessment Matrix

### High Risk

| Risk | Mitigation |
|------|------------|
| LinkedIn ToS / account ban if cookie scraping is shipped | Prohibit LinkedIn cookie tools in PRD; public-web only |
| Hallucinated candidates or emails | Require source URLs; “contact unknown” if not on page; QA tests for empty/unverified |
| Treated as automated hiring decision (EU AI Act / GDPR / NYC AEDT) | Human-in-the-loop; language: recommend, do not decide; no auto-reject |
| Bias in unstructured LLM scoring | Publish a skill/evidence rubric; avoid protected-class proxies (photo, name-origin, school prestige as proxy) |

### Medium Risk

| Risk | Mitigation |
|------|------------|
| Search quality / thin candidate pool | Allow N=5–10; show “insufficient public evidence” |
| LLM cost overruns | `max_iter`, `max_rpm`, `max_execution_time`; smaller default N |
| Market TAM confusion in messaging | Quote ranges and definitions |
| ATS non-integration friction | Export markdown; ATS APIs Future Work |

### Low Risk

| Risk | Mitigation |
|------|------------|
| UI theming | Follow `ui.theme: system`, `visual_style: minimal` from example config |
| Runtime adapter mismatch | Record `AAMAD_TARGET_RUNTIME=crewai`; do not treat CrewAI as AAMAD itself |

---

## Actionable Recommendations

### Immediate next steps (within 48 hours)

1. Approve this MRD scope: employer-side job → candidates crew; chat MVP; no LinkedIn cookies.
2. Author PRD from this MRD (`*create-prd`).
3. Confirm runtime remains `crewai` (env unset → default crewai per adapter registry).

### Short-term priorities (next 30 days / Build)

1. SAD/SFS from `@system.arch`.
2. YAML crew + kickoff API + chat UI + unit/integration tests mapped to acceptance criteria.
3. Security assessment before Deliver.

### Long-term strategy (6–12 months)

1. Official sourcing APIs; ATS export; optional bias-audit logging if used in regulated jurisdictions.
2. Recruiter-owned send channels (never silent send).
3. Evaluate whether commercialization (seats) is desired; until then treat as internal/demo product with market-facing *capability*, not a GTM launch.

---

## Quality notes (research method)

- 20+ named sources below; figures retrieved **2026-10-13**.
- Market sizes **conflict**; conflicts are called out in Dimension 1.
- Quantitative claims tied to named publishers; vendor-funded speed claims labeled as such.
- No primary customer interviews were conducted (limitation → Assumptions).

---

## Sources

1. CrewAI Inc., `crewAI-examples` — Recruitment crew README, agents, tasks, crew, main, `.env.example`. https://github.com/crewAIInc/crewAI-examples/tree/main/crews/recruitment — retrieved 2026-10-13.
2. CrewAI documentation — Examples index (Recruitment: candidate sourcing and evaluation). https://docs.crewai.com/ — retrieved 2026-10-13.
3. Community index of the same crew (tasks/IO summary). https://crewai.jhayer.tech/crew/ai-crew-for-recruitment — retrieved 2026-10-13.
4. CrewAI examples — Match Profile to Positions (CV-to-job; related but inverse). https://github.com/crewAIInc/crewAI-examples/tree/main/crews/match_profile_to_positions — retrieved 2026-10-13.
5. Mordor Intelligence — Recruitment Software Market. https://www.mordorintelligence.com/industry-reports/recruitment-software-market — retrieved 2026-10-13.
6. Mordor Intelligence — Talent Acquisition Software Market. https://www.mordorintelligence.com/industry-reports/talent-acquisition-software-market — retrieved 2026-10-13.
7. Mordor Intelligence — AI Recruitment Market. https://www.mordorintelligence.com/industry-reports/ai-recruitment-market — retrieved 2026-10-13.
8. The Business Research Company via GII — Recruitment Software Global Market Report 2026. https://www.giiresearch.com/report/tbrc1977383-recruitment-software-global-market-report.html — retrieved 2026-10-13.
9. IMARC Group — Global Recruitment Software Market. https://www.imarcgroup.com/global-recruitment-software-market — retrieved 2026-10-13.
10. Coherent Market Insights — Recruitment Software Market press release. https://www.coherentmarketinsights.com/press-release/recruitment-software-market-4876 — retrieved 2026-10-13.
11. Pin — AI in Recruitment Market Size and Growth: 2026 Report (cites Grand View Research). https://www.pin.com/blog/ai-in-recruitment-market/ — retrieved 2026-10-13.
12. LinkedIn Talent Solutions — The Future of Recruiting 2025. https://business.linkedin.com/hire/resources/future-of-recruiting — retrieved 2026-10-13.
13. SHRM — 2025 Benchmarking Reports press release (cost-per-hire, recruiting budget share, screening/interview duration). https://www.shrm.org/about/press-room/shrm-releases-2025-benchmarking-reports--how-does-your-organizat — retrieved 2026-10-13.
14. SHRM Executive Network — The State of Recruiting 2025 (median time-to-fill). https://www.shrm.org/executive-network/insights/people-strategy/state-of-recruiting-2025-insights-to-maximize-recruitment — retrieved 2026-10-13.
15. SmartRecruiters — Recruitment Benchmarks 2025 (global median time-to-hire; AI 26% faster claim). https://www.smartrecruiters.com/resources/article/united-states-benchmark-recruiting-metrics/ and related PDF — retrieved 2026-10-13.
16. Juicebox — 14 Best recruiting software examples (2026) (competitive set). https://juicebox.ai/blog/recruiting-software-examples — retrieved 2026-10-13.
17. European Commission AI Act Service Desk — Annex III (employment/recruitment high-risk). https://ai-act-service-desk.ec.europa.eu/en/ai-act/annex-3 — retrieved 2026-10-13.
18. EU Artificial Intelligence Act — Article 6 classification (incl. profiling). https://artificialintelligenceact.eu/article/6/ — retrieved 2026-10-13.
19. Regulation (EU) 2016/679 (GDPR) Article 22 — automated individual decision-making. https://eur-lex.europa.eu/eli/reg/2016/679/oj — retrieved 2026-10-13.
20. NYC Local Law 144 of 2021 — automated employment decision tools (AEDT). https://www.nyc.gov/site/dca/about/automated-employment-decision-tools.page — retrieved 2026-10-13.
21. AAMAD project templates and rules: `.cursor/templates/mrd-template.md`, `.cursor/rules/adapter-crewai.mdc`, `.cursor/rules/aamad-core.mdc`, `aamad.config.example.yml` — local, 2026-10-13.
22. Stakeholder instruction (this session): create MRD then PRD for a recruitment assistant based on the CrewAI recruitment example — 2026-10-13.

---

## Assumptions

- The product is **market-facing in capability** (a recruiter copilot) even if the immediate operator is internal; therefore MRD is **not** skipped.
- No `aamad.config.yml` is present; preferences inferred from `aamad.config.example.yml` (Python, crewai, minimal UI, security assessment true) unless the operator overrides.
- `AAMAD_TARGET_RUNTIME` was not observed in the environment; resolved default is `crewai` per adapter registry.
- Primary language of job requirements and reports is English.
- ICP for MVP is SME/startup technical recruiting, not healthcare credentialing or high-volume hourly hiring (those appear in market reports but are out of the CrewAI example).
- LinkedIn authenticated scraping is **unacceptable** for the product despite existing in the example.
- No customer interviews; persona pain is inferred from SHRM/LinkedIn/SmartRecruiters plus the example workflow.
- Monetization and GTM are deferred; Launch strategy in PRD may be N/A.

---

## Open Questions

1. Should MVP candidate count default to 10 (example) or 5 (cost/latency)?
2. Which LLM provider is mandated beyond example GPT-4o (OpenAI vs compatible gateway)?
3. Is any **official** people-search API in scope, or public web only?
4. Will the operator require login/multi-user, or single local operator?
5. Geographic hiring jurisdiction (US only vs EU) for how strongly we phrase AI-Act/AEDT warnings in the UI?
6. After PRD, does `@system.arch` own score-rubric schema as SAD, or keep it PRD-level?
7. Copy `aamad.config.yml` from the example before Build?
8. Include job-seeker reverse flow (Match Profile to Positions) as P2 only?

---

## Audit

- **timestamp:** 2026-10-13T03:00:00Z
- **persona id:** `product-mgr`
- **action:** `create-mrd`
- AAMAD_TARGET_RUNTIME: crewai (default; env unset; example config runtime.target: crewai)
- **model / research method:** Cursor Grok 4.6 with web retrieval of market, legal, and CrewAI example sources; temperature not applicable to artifact write
- **runtime controls impacting determinism:** N/A (Define-phase document); recommended later: sequential process, `memory=False`, `max_iter <= 12`, `max_rpm` at crew
- **Prompt Trace:** omitted — research synthesis document, not a production model prompt; source URLs listed above
- **tools:** WebSearch, WebFetch, local template/persona/config reads

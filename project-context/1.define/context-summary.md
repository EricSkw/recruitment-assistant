# Context Summary — Recruitment Assistant (Define handoff)

**Audience:** `@system.arch` and Build personas  
**Commands completed:** `*create-mrd`, `*create-prd` (`*create-context` summary)

## What to build

A **chat MVP** around the CrewAI recruitment example: sequential crew **researcher → matcher → communicator → reporter**. Input is a job-requirements blob; output is a markdown recruiter report (profiles, scores, outreach drafts, sources). Recommendations only; **no** auto-send, **no** auto-reject, **no** LinkedIn cookie/Selenium.

## Runtime

`AAMAD_TARGET_RUNTIME=crewai` (default). YAML agents/tasks, sequential process, `allow_delegation=false`, `memory=False`, iteration/RPM/time caps per adapter.

## Do not copy from the example

`LINKEDIN_COOKIE` / authenticated LinkedIn scrape (example README ToS warning).

## Artifacts

- `project-context/1.define/mrd.md`
- `project-context/1.define/prd.md`
- Next: SAD/SFS (`@system.arch`); optional `*create-stories`

## Sources

- This file summarizes `mrd.md` and `prd.md` (2026-10-13).

## Assumptions

- `aamad.config.yml` absent; example config used as preference hint.
- User stories not generated in this session.

## Open Questions

- Default candidate count (5 vs 10), model pin, config file copy — see PRD Open Questions.

## Audit

- **timestamp:** 2026-10-13T03:20:00Z
- **persona id:** `product-mgr`
- **action:** `create-context` (summary only; MRD+PRD already written)
- AAMAD_TARGET_RUNTIME: crewai

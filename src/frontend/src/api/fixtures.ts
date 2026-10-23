import type { NormalizedJob } from "../types";

export function sampleReport(job: NormalizedJob, assumptions: string[]): string {
  const assumptionLines = assumptions.length > 0 ? assumptions.map((item) => `- ${item}`).join("\n") : "None";
  return [
    "## Job requirements",
    "",
    `Title: ${job.title || "(empty)"}`,
    "",
    "This section repeats the requisition held by the fixture client. It is not a live search.",
    "",
    "## Assumptions",
    "",
    assumptionLines,
    "",
    "## Candidate profiles",
    "",
    "- Fixture Lead A — public handle `fixture-lead-a`. Evidence summary: placeholder layout text only. source_url: https://example.com/fixture-lead-a",
    "",
    "## Ranked scores and justifications",
    "",
    "- Fixture Lead A — score 70/100. The justification cites the written requisition only. This score is a fixture for the chat layout, not a hiring decision.",
    "",
    "## Outreach drafts",
    "",
    "Draft for Fixture Lead A (not sent):",
    "",
    "Hello. This template is a fixture and was not sent.",
    "",
    "## Sources",
    "",
    "- https://example.com/fixture-lead-a",
    "",
    "## Recommendations for recruiter review",
    "",
    "Recommendations require human review. No candidate was rejected or contacted.",
  ].join("\n");
}

export function partialReport(): string {
  return [
    "Partial result.",
    "",
    "Task research_candidates stopped before a shortlist was finished.",
    "No contact details were added.",
    "unverified",
  ].join("\n");
}

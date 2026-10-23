import type { Remote, RunRequest } from "./types";

export type Draft = {
  mode: "fields" | "paste";
  title: string;
  description: string;
  responsibilities: string;
  requirements: string;
  preferred_qualifications: string;
  location: string;
  remote: "" | Remote;
  perks_and_benefits: string;
  raw_blob: string;
  candidate_limit: string;
};

export function emptyDraft(): Draft {
  return {
    mode: "fields",
    title: "",
    description: "",
    responsibilities: "",
    requirements: "",
    preferred_qualifications: "",
    location: "",
    remote: "",
    perks_and_benefits: "",
    raw_blob: "",
    candidate_limit: "10",
  };
}

export function exampleDraft(): Draft {
  return {
    mode: "fields",
    title: "Senior Backend Engineer",
    description: "Build and maintain HTTP APIs for an internal hiring tool.",
    responsibilities: "Design endpoints, review tests, and write operator notes.",
    requirements: "Python, FastAPI, PostgreSQL",
    preferred_qualifications: "TypeScript",
    location: "Lisbon",
    remote: "hybrid",
    perks_and_benefits: "",
    raw_blob: "",
    candidate_limit: "10",
  };
}

export function draftToRequest(draft: Draft): RunRequest {
  const parsed = Number(draft.candidate_limit);
  const candidate_limit = Number.isFinite(parsed) ? parsed : Number.NaN;
  if (draft.mode === "paste") {
    return {
      job_requirements: null,
      raw_blob: draft.raw_blob,
      confirm_run_anyway: false,
      candidate_limit,
    };
  }
  return {
    job_requirements: {
      title: draft.title,
      description: draft.description,
      responsibilities: draft.responsibilities,
      requirements: draft.requirements,
      preferred_qualifications: draft.preferred_qualifications || null,
      location: draft.location || null,
      remote: draft.remote || null,
      perks_and_benefits: draft.perks_and_benefits || null,
    },
    raw_blob: null,
    confirm_run_anyway: false,
    candidate_limit,
  };
}

export function requestSummary(request: RunRequest): string {
  if (request.raw_blob && !request.job_requirements) return request.raw_blob;
  const job = request.job_requirements;
  if (!job) return "(empty requisition)";
  const lines = [
    `Title: ${job.title?.trim() || "(empty)"}`,
    `Must-haves: ${job.requirements?.trim() || "(empty)"}`,
    job.description?.trim() ? `Description: ${job.description.trim()}` : null,
    job.responsibilities?.trim() ? `Responsibilities: ${job.responsibilities.trim()}` : null,
    job.preferred_qualifications?.trim()
      ? `Preferred: ${job.preferred_qualifications.trim()}`
      : null,
    job.location?.trim() ? `Location: ${job.location.trim()}` : null,
    job.remote ? `Remote: ${job.remote}` : null,
    job.perks_and_benefits?.trim() ? `Perks: ${job.perks_and_benefits.trim()}` : null,
    `Candidates: ${request.candidate_limit ?? 10}`,
  ];
  return lines.filter((line): line is string => Boolean(line)).join("\n");
}

export type Remote = "onsite" | "hybrid" | "remote";

export type JobRequirements = {
  title?: string | null;
  description?: string | null;
  responsibilities?: string | null;
  requirements?: string | null;
  preferred_qualifications?: string | null;
  location?: string | null;
  remote?: Remote | null;
  perks_and_benefits?: string | null;
};

export type RunRequest = {
  job_requirements?: JobRequirements | null;
  raw_blob?: string | null;
  confirm_run_anyway?: boolean;
  candidate_limit?: number | null;
};

export type Gap = {
  field: string;
  reason: string;
  run_anyway_allowed: boolean;
};

export type ErrorCode =
  | "VALIDATION"
  | "MISSING_API_KEY"
  | "CREW_BUSY"
  | "TIMEOUT"
  | "CREW_FAILURE"
  | "GUARDRAIL";

export type ErrorBody = {
  code: ErrorCode;
  message: string;
  run_id: string | null;
};

export type ErrorEnvelope = {
  error: ErrorBody;
};

export type TaskId =
  | "research_candidates"
  | "match_and_score"
  | "draft_outreach"
  | "compile_report";

export type AcceptedBody = {
  run_id: string;
  status: "queued";
  gaps: [];
};

export type ClarificationBody = {
  run_id: null;
  status: "needs_clarification";
  gaps: Gap[];
};

export type RunBody = {
  run_id: string;
  status: "queued" | "running" | "completed" | "failed" | "partial";
  current_task: TaskId | null;
  partial: boolean;
  assumptions: string[];
  report_markdown: string | null;
  error: ErrorBody | null;
};

export type SubmitResult =
  | { http: 202; body: AcceptedBody }
  | { http: 200; body: ClarificationBody }
  | { http: 422 | 409 | 503; body: ErrorEnvelope };

export type GetResult = { http: 200; body: RunBody } | { http: 404; body: ErrorEnvelope };

export type PreviewKind =
  | "sample"
  | "missing_key"
  | "busy"
  | "timeout"
  | "guardrail"
  | "partial"
  | "zero_hits"
  | "crew_failure";

export type NormalizedJob = {
  title: string;
  description: string;
  responsibilities: string;
  requirements: string;
  preferred_qualifications: string;
  location: string;
  remote: Remote | null;
  perks_and_benefits: string;
};

export const TASK_LABELS: Record<TaskId, string> = {
  research_candidates: "Researcher",
  match_and_score: "Evaluator (matcher)",
  draft_outreach: "Recommender (communicator)",
  compile_report: "Recommender (reporter)",
};

export const REVIEW_NOTICE =
  "Recommendations require human review. This app does not reject or contact candidates.";

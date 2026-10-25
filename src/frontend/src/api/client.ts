import type {
  AcceptedBody,
  ClarificationBody,
  ErrorCode,
  ErrorEnvelope,
  GetResult,
  RunBody,
  RunRequest,
  SubmitResult,
  TaskId,
} from "../types";

export const POLL_INTERVAL_MS = 2000;

const ERROR_CODES: readonly ErrorCode[] = [
  "VALIDATION",
  "MISSING_API_KEY",
  "CREW_BUSY",
  "TIMEOUT",
  "CREW_FAILURE",
  "GUARDRAIL",
];

const TASKS: readonly TaskId[] = [
  "research_candidates",
  "match_and_score",
  "draft_outreach",
  "compile_report",
];

const RUN_STATUSES = ["queued", "running", "completed", "failed", "partial"] as const;

export function apiUrl(path: string): string {
  const base = (import.meta.env.VITE_API_BASE ?? "").replace(/\/$/, "");
  return `${base}${path}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function asCode(value: unknown): ErrorCode {
  return ERROR_CODES.find((code) => code === value) ?? "CREW_FAILURE";
}

function asError(value: unknown, fallback: string): ErrorEnvelope {
  if (!isRecord(value) || !isRecord(value.error) || typeof value.error.message !== "string") {
    return { error: { code: "CREW_FAILURE", message: fallback, run_id: null } };
  }
  const runId = value.error.run_id;
  return {
    error: {
      code: asCode(value.error.code),
      message: value.error.message,
      run_id: typeof runId === "string" ? runId : null,
    },
  };
}

function isClarification(value: unknown): value is ClarificationBody {
  if (!isRecord(value) || value.status !== "needs_clarification" || value.run_id !== null) {
    return false;
  }
  if (!Array.isArray(value.gaps)) return false;
  return value.gaps.every(
    (gap) =>
      isRecord(gap) &&
      typeof gap.field === "string" &&
      typeof gap.reason === "string" &&
      typeof gap.run_anyway_allowed === "boolean",
  );
}

function isAccepted(value: unknown): value is AcceptedBody {
  return (
    isRecord(value) &&
    value.status === "queued" &&
    typeof value.run_id === "string" &&
    Array.isArray(value.gaps) &&
    value.gaps.length === 0
  );
}

function isTask(value: unknown): value is TaskId | null {
  return value === null || TASKS.some((task) => task === value);
}

function isRunBody(value: unknown): value is RunBody {
  if (!isRecord(value) || typeof value.run_id !== "string") return false;
  if (!RUN_STATUSES.some((status) => status === value.status)) return false;
  if (!isTask(value.current_task) || typeof value.partial !== "boolean") return false;
  if (!Array.isArray(value.assumptions) || !value.assumptions.every((item) => typeof item === "string")) {
    return false;
  }
  if (value.report_markdown !== null && typeof value.report_markdown !== "string") return false;
  if (value.error === null) return true;
  return isRecord(value.error) && typeof value.error.message === "string";
}

async function readJson(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return null;
  }
}

async function call(path: string, init?: RequestInit): Promise<{ http: number; body: unknown }> {
  try {
    const response = await fetch(apiUrl(path), {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...init?.headers,
      },
    });
    return { http: response.status, body: await readJson(response) };
  } catch {
    return { http: 0, body: null };
  }
}

const UNREADABLE = "The API returned a response the page could not read.";
const UNREACHABLE = "The API could not be reached. Start the backend on 127.0.0.1:8000.";

export async function submitRun(request: RunRequest): Promise<SubmitResult> {
  const result = await call("/api/runs", { method: "POST", body: JSON.stringify(request) });
  if (result.http === 0) {
    return { http: 503, body: asError(null, UNREACHABLE) };
  }
  if (result.http === 202 && isAccepted(result.body)) {
    return { http: 202, body: result.body };
  }
  if (result.http === 200 && isClarification(result.body)) {
    return { http: 200, body: result.body };
  }
  const envelope = asError(result.body, UNREADABLE);
  if (result.http === 422 || result.http === 409 || result.http === 503) {
    return { http: result.http, body: envelope };
  }
  return { http: 503, body: envelope };
}

export async function getRun(runId: string): Promise<GetResult> {
  const result = await call(`/api/runs/${encodeURIComponent(runId)}`);
  if (result.http === 200 && isRunBody(result.body)) {
    return { http: 200, body: result.body };
  }
  if (result.http === 0) {
    return { http: 404, body: asError(null, UNREACHABLE) };
  }
  return { http: 404, body: asError(result.body, result.http === 404 ? "Unknown run id." : UNREADABLE) };
}

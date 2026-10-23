import { gapMessage, PayloadError, prepareRequest } from "./previewGate";
import { partialReport, sampleReport } from "./fixtures";
import type {
  ErrorEnvelope,
  GetResult,
  NormalizedJob,
  PreviewKind,
  RunBody,
  RunRequest,
  SubmitResult,
  TaskId,
} from "../types";

export const POLL_INTERVAL_MS = 2000;

const TASKS: TaskId[] = [
  "research_candidates",
  "match_and_score",
  "draft_outreach",
  "compile_report",
];

type StoredRun = {
  id: string;
  startedAt: number;
  preview: PreviewKind;
  assumptions: string[];
  job: NormalizedJob;
};

let nowFn = () => Date.now();
const runs = new Map<string, StoredRun>();

export function setStubClock(fn: () => number): void {
  nowFn = fn;
}

export function resetStub(): void {
  runs.clear();
  nowFn = () => Date.now();
}

function envelope(
  code: ErrorEnvelope["error"]["code"],
  message: string,
  runId: string | null = null,
): ErrorEnvelope {
  return { error: { code, message, run_id: runId } };
}

function validation(message: string): SubmitResult {
  return { http: 422, body: envelope("VALIDATION", message) };
}

function project(run: StoredRun, now: number): RunBody {
  const step = Math.floor(Math.max(0, now - run.startedAt) / POLL_INTERVAL_MS);
  const base = {
    run_id: run.id,
    assumptions: run.assumptions,
    partial: false,
    report_markdown: null,
    error: null,
  };

  if (run.preview === "timeout" && step >= 2) {
    return {
      ...base,
      status: "failed",
      current_task: "research_candidates",
      error: {
        code: "TIMEOUT",
        message: "Kickoff exceeded the time limit. Last task: research_candidates.",
        run_id: run.id,
      },
    };
  }

  if (step <= 0) {
    return { ...base, status: "queued", current_task: null };
  }

  if (step <= TASKS.length) {
    const task = TASKS[step - 1];
    if (!task) {
      return { ...base, status: "queued", current_task: null };
    }
    return { ...base, status: "running", current_task: task };
  }

  if (run.preview === "guardrail") {
    return {
      ...base,
      status: "failed",
      current_task: "compile_report",
      error: {
        code: "GUARDRAIL",
        message: "Report guardrail failed. The report was not published.",
        run_id: run.id,
      },
    };
  }

  if (run.preview === "zero_hits") {
    return {
      ...base,
      status: "failed",
      current_task: "research_candidates",
      error: {
        code: "CREW_FAILURE",
        message: "Search returned zero public hits. No candidates were added.",
        run_id: run.id,
      },
    };
  }

  if (run.preview === "partial") {
    return {
      ...base,
      status: "partial",
      partial: true,
      current_task: "research_candidates",
      report_markdown: partialReport(),
      error: {
        code: "CREW_FAILURE",
        message:
          "The crew stopped after research_candidates. Partial text is labeled and was not filled in.",
        run_id: run.id,
      },
    };
  }

  return {
    ...base,
    status: "completed",
    current_task: "compile_report",
    report_markdown: sampleReport(run.job, run.assumptions),
  };
}

function isActive(run: StoredRun, now: number): boolean {
  const status = project(run, now).status;
  return status === "queued" || status === "running";
}

function checkLimit(request: RunRequest): SubmitResult | null {
  if (request.candidate_limit == null) return null;
  const limit = request.candidate_limit;
  if (!Number.isInteger(limit) || limit < 5 || limit > 10) {
    return validation("candidate_limit must be an integer from 5 to 10.");
  }
  return null;
}

export async function submitRun(request: RunRequest, preview: PreviewKind): Promise<SubmitResult> {
  const limitError = checkLimit(request);
  if (limitError) return limitError;
  if (preview === "missing_key") {
    return {
      http: 503,
      body: envelope(
        "MISSING_API_KEY",
        "Missing required environment variable: OPENAI_API_KEY, SERPER_API_KEY.",
      ),
    };
  }
  if (preview === "crew_failure") {
    return {
      http: 503,
      body: envelope("CREW_FAILURE", "The crew failed to load."),
    };
  }

  let prepared;
  try {
    prepared = prepareRequest(request);
  } catch (error) {
    const message = error instanceof PayloadError ? error.message : "Job requirements are invalid.";
    return validation(message);
  }

  if (prepared.status === "blocked") {
    return validation(gapMessage(prepared.gaps));
  }
  if (prepared.status === "needs_clarification") {
    return {
      http: 200,
      body: { run_id: null, status: "needs_clarification", gaps: prepared.gaps },
    };
  }

  const now = nowFn();
  const active = [...runs.values()].some((run) => isActive(run, now));
  if (preview === "busy" || active) {
    return {
      http: 409,
      body: envelope("CREW_BUSY", "A crew is already active. Wait until it finishes."),
    };
  }

  const id = crypto.randomUUID();
  runs.set(id, {
    id,
    startedAt: now,
    preview,
    assumptions: prepared.assumptions,
    job: prepared.job,
  });
  return { http: 202, body: { run_id: id, status: "queued", gaps: [] } };
}

export async function getRun(runId: string): Promise<GetResult> {
  const run = runs.get(runId);
  if (!run) {
    return {
      http: 404,
      body: envelope("VALIDATION", "Unknown run id.", runId),
    };
  }
  return { http: 200, body: project(run, nowFn()) };
}

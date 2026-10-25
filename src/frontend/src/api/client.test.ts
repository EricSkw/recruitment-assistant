import { afterEach, describe, expect, it, vi } from "vitest";
import { apiUrl, getRun, POLL_INTERVAL_MS, submitRun } from "./client";
import type { RunRequest } from "../types";

function request(overrides: Partial<RunRequest> = {}): RunRequest {
  return {
    job_requirements: {
      title: "Senior Rails Engineer",
      description: "Build the product.",
      responsibilities: "Ship features.",
      requirements: "Ruby on Rails PostgreSQL",
      location: "Austin",
      remote: "hybrid",
    },
    confirm_run_anyway: false,
    candidate_limit: 10,
    ...overrides,
  };
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api client", () => {
  it("posts the requisition to /api/runs and accepts a queued run", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      expect(String(input)).toBe(apiUrl("/api/runs"));
      expect(init?.method).toBe("POST");
      expect(JSON.parse(String(init?.body))).toMatchObject({ candidate_limit: 10 });
      return jsonResponse(202, { run_id: "run-1", status: "queued", gaps: [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    const result = await submitRun(request());
    expect(result.http).toBe(202);
    if (result.http !== 202) return;
    expect(result.body.run_id).toBe("run-1");
  });

  it("returns clarification without a run id", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse(200, {
          run_id: null,
          status: "needs_clarification",
          gaps: [{ field: "seniority", reason: "Add a level.", run_anyway_allowed: true }],
        }),
      ),
    );
    const result = await submitRun(request());
    expect(result.http).toBe(200);
    if (result.http !== 200) return;
    expect(result.body.run_id).toBeNull();
    expect(result.body.gaps[0]?.field).toBe("seniority");
  });

  it("keeps validation, busy, and missing-key envelopes", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(
          jsonResponse(422, {
            error: { code: "VALIDATION", message: "title: required", run_id: null },
          }),
        )
        .mockResolvedValueOnce(
          jsonResponse(409, {
            error: { code: "CREW_BUSY", message: "A crew is already active.", run_id: null },
          }),
        )
        .mockResolvedValueOnce(
          jsonResponse(503, {
            error: {
              code: "MISSING_API_KEY",
              message: "Missing required environment variable: OPENAI_API_KEY.",
              run_id: null,
            },
          }),
        ),
    );
    const validation = await submitRun(request());
    const busy = await submitRun(request());
    const missing = await submitRun(request());
    expect(validation.http).toBe(422);
    expect(busy.http).toBe(409);
    expect(missing.http).toBe(503);
    if (missing.http !== 503) return;
    expect(missing.body.error.code).toBe("MISSING_API_KEY");
  });

  it("polls a run and surfaces an unknown id", async () => {
    expect(POLL_INTERVAL_MS).toBe(2000);
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(
          jsonResponse(200, {
            run_id: "run-1",
            status: "running",
            current_task: "research_candidates",
            partial: false,
            assumptions: [],
            report_markdown: null,
            error: null,
          }),
        )
        .mockResolvedValueOnce(
          jsonResponse(200, {
            run_id: "run-1",
            status: "completed",
            current_task: "compile_report",
            partial: false,
            assumptions: ["Location was not stated."],
            report_markdown: "## Recommendations for recruiter review\n\nDraft was not sent.",
            error: null,
          }),
        )
        .mockResolvedValueOnce(
          jsonResponse(404, { error: { code: "VALIDATION", message: "Unknown run id.", run_id: "missing" } }),
        ),
    );
    const running = await getRun("run-1");
    const done = await getRun("run-1");
    const missing = await getRun("missing");
    expect(running.http).toBe(200);
    if (running.http === 200) expect(running.body.current_task).toBe("research_candidates");
    expect(done.http).toBe(200);
    if (done.http === 200) {
      expect(done.body.report_markdown).toContain("not sent");
      expect(done.body.report_markdown?.startsWith("```")).toBe(false);
    }
    expect(missing.http).toBe(404);
    if (missing.http === 404) expect(missing.body.error.message).toBe("Unknown run id.");
  });

  it("reports an unreachable API without throwing", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network");
      }),
    );
    const result = await submitRun(request());
    expect(result.http).toBe(503);
    if (result.http !== 503) return;
    expect(result.body.error.code).toBe("CREW_FAILURE");
    expect(result.body.error.message).toContain("127.0.0.1:8000");
  });
});

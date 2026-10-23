import { afterEach, describe, expect, it } from "vitest";
import { getRun, resetStub, setStubClock, submitRun } from "./client";
import { sampleReport } from "./fixtures";
import {
  ASSUMPTION_LOCATION,
  ASSUMPTION_SENIORITY,
  evaluateGate,
  mergeRequirements,
  mustHavesEmpty,
  normalizeRequirements,
  parseRawBlob,
  prepareRequest,
} from "./previewGate";
import type { NormalizedJob, RunRequest } from "../types";

function job(overrides: Partial<NormalizedJob> = {}): NormalizedJob {
  return normalizeRequirements({
    title: "Rails Engineer",
    description: "Build the product.",
    responsibilities: "Ship features.",
    requirements: "Ruby on Rails PostgreSQL",
    preferred_qualifications: "",
    location: "Austin",
    remote: "hybrid",
    perks_and_benefits: "",
    ...overrides,
  });
}

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

afterEach(() => {
  resetStub();
});

describe("preview gate", () => {
  it("blocks an empty title even when run anyway is set", () => {
    const result = evaluateGate(job({ title: " " }), true);
    expect(result.status).toBe("blocked");
    expect(result.gaps[0]?.run_anyway_allowed).toBe(false);
  });

  it("treats vague must-haves as empty", () => {
    expect(mustHavesEmpty("good culture fit, team player, rockstar")).toBe(true);
    expect(mustHavesEmpty("a passionate ninja")).toBe(true);
    expect(mustHavesEmpty("Ruby on Rails PostgreSQL")).toBe(false);
    const result = evaluateGate(job({ requirements: "good culture fit" }), true);
    expect(result.status).toBe("blocked");
  });

  it("asks for seniority and location before kickoff", () => {
    const result = evaluateGate(job({ title: "Rails Engineer", location: "", remote: null }), false);
    expect(result.status).toBe("needs_clarification");
    expect(result.gaps.map((gap) => gap.field).sort()).toEqual(["location", "seniority"]);
  });

  it("records assumptions when run anyway is confirmed", () => {
    const result = evaluateGate(job({ title: "Rails Engineer", location: "", remote: null }), true);
    expect(result.status).toBe("ok");
    expect(result.assumptions).toEqual([ASSUMPTION_SENIORITY, ASSUMPTION_LOCATION]);
  });

  it("lets explicit fields override the paste", () => {
    const blob = parseRawBlob("title: Junior Analyst\nrequirements: SQL Excel Python\n");
    const merged = normalizeRequirements(mergeRequirements(blob, { title: "Senior Analyst" }));
    expect(merged.title).toBe("Senior Analyst");
    expect(merged.requirements).toBe("SQL Excel Python");
  });

  it("rejects invalid YAML and unknown fields", () => {
    expect(() => parseRawBlob("title: [unterminated")).toThrow(/YAML/);
    expect(() => parseRawBlob("- just a list")).toThrow(/mapping/);
    expect(() => prepareRequest({ raw_blob: "salary: 1\ntitle: Senior Analyst\nrequirements: SQL Excel Python\nlocation: Austin\n", candidate_limit: 10 })).toThrow(/Unknown job field/);
  });
});

describe("fixture client", () => {
  it("does not call fetch", async () => {
    const original = globalThis.fetch;
    globalThis.fetch = () => {
      throw new Error("network");
    };
    try {
      const result = await submitRun(request(), "sample");
      expect(result.http).toBe(202);
    } finally {
      globalThis.fetch = original;
    }
  });

  it("returns clarification without a run id", async () => {
    const result = await submitRun(
      request({
        job_requirements: {
          title: "Rails Engineer",
          description: "Build the product.",
          responsibilities: "Ship features.",
          requirements: "Ruby on Rails PostgreSQL",
          location: null,
          remote: null,
        },
      }),
      "sample",
    );
    expect(result.http).toBe(200);
    if (result.http !== 200) return;
    expect(result.body.run_id).toBeNull();
    expect(result.body.gaps.length).toBeGreaterThan(0);
  });

  it("walks task names and then returns the sample report", async () => {
    let time = 1_000;
    setStubClock(() => time);
    const accepted = await submitRun(request(), "sample");
    expect(accepted.http).toBe(202);
    if (accepted.http !== 202) return;
    const queued = await getRun(accepted.body.run_id);
    expect(queued.http).toBe(200);
    if (queued.http !== 200) return;
    expect(queued.body.status).toBe("queued");

    const seen: string[] = [];
    for (const step of [2_000, 4_000, 6_000, 8_000]) {
      time = 1_000 + step;
      const view = await getRun(accepted.body.run_id);
      if (view.http === 200 && view.body.current_task) seen.push(view.body.current_task);
    }
    expect(seen).toEqual([
      "research_candidates",
      "match_and_score",
      "draft_outreach",
      "compile_report",
    ]);

    time = 1_000 + 10_000;
    const done = await getRun(accepted.body.run_id);
    expect(done.http).toBe(200);
    if (done.http !== 200) return;
    expect(done.body.status).toBe("completed");
    expect(done.body.report_markdown).toContain("not sent");
    expect(done.body.report_markdown).toContain("## Sources");
    expect(done.body.report_markdown?.startsWith("```")).toBe(false);
  });

  it("names the last task on timeout and can show a missing key", async () => {
    let time = 0;
    setStubClock(() => time);
    const accepted = await submitRun(request(), "timeout");
    expect(accepted.http).toBe(202);
    if (accepted.http !== 202) return;
    time = 4_000;
    const failed = await getRun(accepted.body.run_id);
    expect(failed.http).toBe(200);
    if (failed.http !== 200) return;
    expect(failed.body.status).toBe("failed");
    expect(failed.body.error?.code).toBe("TIMEOUT");
    expect(failed.body.error?.message).toContain("research_candidates");

    const missing = await submitRun(request({ job_requirements: { title: "" } }), "missing_key");
    expect(missing.http).toBe(503);
    if (missing.http !== 503) return;
    expect(missing.body.error.code).toBe("MISSING_API_KEY");
  });

  it("rejects a second run while one is active", async () => {
    let time = 0;
    setStubClock(() => time);
    const first = await submitRun(request(), "sample");
    expect(first.http).toBe(202);
    const second = await submitRun(request(), "sample");
    expect(second.http).toBe(409);
    time = 20_000;
    const third = await submitRun(request(), "sample");
    expect(third.http).toBe(202);
  });

  it("keeps the sample report free of a code fence", () => {
    const report = sampleReport(job({ title: "Senior Rails Engineer" }), []);
    expect(report.startsWith("```")).toBe(false);
    expect(report).toContain("## Recommendations for recruiter review");
  });
});

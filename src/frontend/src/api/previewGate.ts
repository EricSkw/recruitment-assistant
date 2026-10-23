import { parse as parseYaml } from "yaml";
import type { Gap, JobRequirements, NormalizedJob, Remote, RunRequest } from "../types";

const PAYLOAD_MAX = 12_000;
const TITLE_MAX = 200;
const FIELD_MAX = 4_000;
const MIN_MUST_HAVE_TOKENS = 3;

const TEXT_FIELDS = [
  "title",
  "description",
  "responsibilities",
  "requirements",
  "preferred_qualifications",
  "location",
  "perks_and_benefits",
] as const;

const REMOTE_VALUES = new Set<Remote>(["onsite", "hybrid", "remote"]);

const VAGUE_PHRASES = [
  "good culture fit",
  "culture fit",
  "team player",
  "rockstar",
  "ninja",
  "fast learner",
  "self-starter",
  "self starter",
  "passionate",
  "passion",
  "go-getter",
  "go getter",
  "wear many hats",
  "hit the ground running",
  "work hard play hard",
];

const STOPWORDS = new Set([
  "a",
  "an",
  "the",
  "and",
  "or",
  "of",
  "to",
  "for",
  "with",
  "in",
  "on",
  "be",
]);

const SENIORITY_TERMS = [
  "intern",
  "junior",
  "jr",
  "mid-level",
  "mid level",
  "senior",
  "sr",
  "staff",
  "principal",
  "lead",
  "manager",
  "director",
  "vp",
  "executive",
  "entry-level",
  "entry level",
];

const LOCATION_TERMS = ["remote", "hybrid", "onsite", "on-site", "work from home", "wfh"];

export const ASSUMPTION_SENIORITY =
  "seniority unspecified; matcher must mark seniority fit as not assessed";
export const ASSUMPTION_LOCATION =
  "location unspecified; search the public web without a geography penalty";

const TOKEN = /[A-Za-z0-9]+/g;
const SENIORITY_YEARS = /\b\d+\+?\s*years?\b/i;

export class PayloadError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "PayloadError";
  }
}

export type GateResult = {
  status: "blocked" | "needs_clarification" | "ok";
  gaps: Gap[];
  assumptions: string[];
  job: NormalizedJob;
};

function isPhrase(raw: string | null | undefined): boolean {
  return (raw ?? "").trim().toLowerCase() === "run anyway";
}

export function confirmationRequested(request: RunRequest): boolean {
  return request.confirm_run_anyway === true || isPhrase(request.raw_blob);
}

export function parseRawBlob(raw: string | null | undefined): Record<string, unknown> {
  if (raw == null || raw.trim() === "") return {};
  if (raw.length > PAYLOAD_MAX) {
    throw new PayloadError("Serialized payload exceeds 12000 characters.");
  }
  if (isPhrase(raw)) return {};
  let loaded: unknown;
  try {
    loaded = parseYaml(raw);
  } catch {
    throw new PayloadError("raw_blob is not valid YAML.");
  }
  if (loaded == null) return {};
  if (typeof loaded !== "object" || Array.isArray(loaded)) {
    throw new PayloadError("raw_blob must be a YAML mapping of job fields.");
  }
  return Object.fromEntries(Object.entries(loaded).map(([key, value]) => [String(key), value]));
}

function explicitRecord(job: JobRequirements): Record<string, unknown> {
  return Object.fromEntries(Object.entries(job).filter(([, value]) => value !== undefined));
}

export function mergeRequirements(
  blob: Record<string, unknown>,
  explicit: Record<string, unknown> | null,
): Record<string, unknown> {
  return { ...blob, ...(explicit ?? {}) };
}

function asRemote(value: unknown): Remote | null {
  if (value == null || value === "") return null;
  if (typeof value === "string" && REMOTE_VALUES.has(value as Remote)) {
    return value as Remote;
  }
  throw new PayloadError("remote must be onsite, hybrid, remote, or null.");
}

export function normalizeRequirements(raw: Record<string, unknown>): NormalizedJob {
  const allowed = new Set<string>([...TEXT_FIELDS, "remote"]);
  const unknown = Object.keys(raw).filter((key) => !allowed.has(key));
  if (unknown.length > 0) {
    throw new PayloadError(`Unknown job field: ${unknown.sort().join(", ")}.`);
  }
  const normalized: Record<string, unknown> = {};
  for (const key of TEXT_FIELDS) {
    const value = raw[key];
    if (value == null) {
      normalized[key] = "";
      continue;
    }
    if (typeof value !== "string") {
      throw new PayloadError(`${key} must be a string.`);
    }
    const text = value.trim();
    const limit = key === "title" ? TITLE_MAX : FIELD_MAX;
    if (text.length > limit) {
      throw new PayloadError(`${key} exceeds ${limit} characters.`);
    }
    normalized[key] = text;
  }
  normalized.remote = asRemote(raw.remote);
  const serialized = JSON.stringify(normalized, Object.keys(normalized).sort());
  if (serialized.length > PAYLOAD_MAX) {
    throw new PayloadError("Serialized payload exceeds 12000 characters.");
  }
  return normalized as NormalizedJob;
}

export function mustHavesEmpty(requirements: string): boolean {
  let text = requirements;
  const phrases = [...VAGUE_PHRASES].sort((a, b) => b.length - a.length);
  for (const phrase of phrases) {
    text = text.replace(new RegExp(phrase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi"), " ");
  }
  const tokens = text.match(TOKEN) ?? [];
  const kept = tokens.filter((token) => !STOPWORDS.has(token.toLowerCase()));
  return kept.length < MIN_MUST_HAVE_TOKENS;
}

function combined(job: NormalizedJob): string {
  return [job.title, job.description, job.responsibilities, job.requirements]
    .filter((part) => part)
    .join("\n");
}

function containsTerm(text: string, term: string): boolean {
  const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`(?<![A-Za-z0-9])${escaped}(?![A-Za-z0-9])`, "i").test(text);
}

function seniorityPresent(job: NormalizedJob): boolean {
  const text = combined(job);
  if (SENIORITY_YEARS.test(text)) return true;
  return SENIORITY_TERMS.some((term) => containsTerm(text, term));
}

function locationPresent(job: NormalizedJob): boolean {
  if (job.location.trim()) return true;
  if (job.remote) return true;
  const text = combined(job);
  return LOCATION_TERMS.some((term) => containsTerm(text, term));
}

export function evaluateGate(job: NormalizedJob, confirm: boolean): GateResult {
  const hard: Gap[] = [];
  if (job.title.trim().length < 2) {
    hard.push({
      field: "title",
      reason: "Title is required and must be at least 2 characters.",
      run_anyway_allowed: false,
    });
  }
  if (mustHavesEmpty(job.requirements)) {
    hard.push({
      field: "requirements",
      reason:
        "Must-have skills are empty after removing vague phrases. Add observable requirements.",
      run_anyway_allowed: false,
    });
  }
  if (hard.length > 0) {
    return { status: "blocked", gaps: hard, assumptions: [], job };
  }
  const clarify: Gap[] = [];
  if (!seniorityPresent(job)) {
    clarify.push({
      field: "seniority",
      reason: "Seniority is missing. Add a level or years of experience, or confirm run anyway.",
      run_anyway_allowed: true,
    });
  }
  if (!locationPresent(job)) {
    clarify.push({
      field: "location",
      reason: "Location or remote constraint is missing. Add it, or confirm run anyway.",
      run_anyway_allowed: true,
    });
  }
  if (clarify.length > 0 && !confirm) {
    return { status: "needs_clarification", gaps: clarify, assumptions: [], job };
  }
  const assumptions: string[] = [];
  if (clarify.some((gap) => gap.field === "seniority")) assumptions.push(ASSUMPTION_SENIORITY);
  if (clarify.some((gap) => gap.field === "location")) assumptions.push(ASSUMPTION_LOCATION);
  return { status: "ok", gaps: [], assumptions, job };
}

export function prepareRequest(request: RunRequest): GateResult {
  const confirm = confirmationRequested(request);
  const skipBlob = confirm && isPhrase(request.raw_blob);
  const blob = parseRawBlob(skipBlob ? null : request.raw_blob);
  const explicit = request.job_requirements ? explicitRecord(request.job_requirements) : null;
  const job = normalizeRequirements(mergeRequirements(blob, explicit));
  return evaluateGate(job, confirm);
}

export function gapMessage(gaps: Gap[]): string {
  const pieces = gaps.map((gap) => `${gap.field}: ${gap.reason}`);
  return `Job requirements are incomplete. ${pieces.join(" ")}`;
}

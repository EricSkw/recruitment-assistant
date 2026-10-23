import { useEffect, useRef, useState } from "react";
import { getRun, POLL_INTERVAL_MS, submitRun } from "../api/client";
import { emptyDraft, requestSummary } from "../draft";
import type { ErrorBody, Gap, PreviewKind, RunRequest, TaskId } from "../types";
import type { TranscriptItem } from "../components/ChatTranscript";
import type { Phase } from "../components/RunStatus";

function nextId(seq: { current: number }): string {
  seq.current += 1;
  return `m${seq.current}`;
}

function gapText(gaps: Gap[]): string {
  const lines = gaps.map((gap) => {
    const allow = gap.run_anyway_allowed
      ? "You can add the detail or confirm run anyway."
      : "Run anyway is not available for this gap.";
    return `${gap.field}: ${gap.reason} ${allow}`;
  });
  return `The crew was not started.\n${lines.join("\n")}`;
}

export function useChatSession() {
  const [draft, setDraft] = useState(emptyDraft);
  const [preview, setPreview] = useState<PreviewKind>("sample");
  const [phase, setPhase] = useState<Phase>("empty");
  const [messages, setMessages] = useState<TranscriptItem[]>([]);
  const [task, setTask] = useState<TaskId | null>(null);
  const [queued, setQueued] = useState(false);
  const [gaps, setGaps] = useState<Gap[]>([]);
  const [error, setError] = useState<ErrorBody | null>(null);
  const [assumptions, setAssumptions] = useState<string[]>([]);
  const [partial, setPartial] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [lastRequest, setLastRequest] = useState<RunRequest | null>(null);
  const seq = useRef(0);
  const previewRef = useRef(preview);
  const settled = useRef<string | null>(null);
  const fieldRef = useRef<HTMLInputElement | HTMLTextAreaElement | null>(null);
  previewRef.current = preview;

  useEffect(() => {
    if (phase !== "in_progress" || !runId) return;
    let cancelled = false;
    const pull = async () => {
      const result = await getRun(runId);
      if (cancelled) return;
      if (result.http === 404) {
        setPhase("error");
        setError(result.body.error);
        setQueued(false);
        setMessages((prev) => [
          ...prev,
          {
            id: nextId(seq),
            role: "assistant",
            body: `${result.body.error.code}: ${result.body.error.message}`,
          },
        ]);
        return;
      }
      const body = result.body;
      setAssumptions(body.assumptions);
      setPartial(body.partial);
      setQueued(body.status === "queued");
      setTask(body.current_task);
      if (body.status === "queued" || body.status === "running") return;
      if (settled.current === body.run_id) return;
      settled.current = body.run_id;
      if (body.status === "completed" || body.status === "partial") {
        setPhase("completed");
        setError(body.error);
        setMessages((prev) => [
          ...prev,
          {
            id: nextId(seq),
            role: "assistant",
            body: body.partial
              ? "Partial result. The text below is incomplete, and nothing was filled in silently."
              : "Recruiter report. Recommendations require human review. Outreach was not sent.",
            markdown: body.report_markdown ?? "",
            partial: body.partial,
            runId: body.run_id,
          },
        ]);
        return;
      }
      setPhase("error");
      setError(body.error);
      setMessages((prev) => [
        ...prev,
        {
          id: nextId(seq),
          role: "assistant",
          body: body.error
            ? `${body.error.code}: ${body.error.message}`
            : "The run failed.",
        },
      ]);
    };
    void pull();
    const timer = window.setInterval(() => void pull(), POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [phase, runId]);

  async function send(request: RunRequest, userText: string) {
    settled.current = null;
    setSending(true);
    setMessages((prev) => [...prev, { id: nextId(seq), role: "user", body: userText }]);
    setLastRequest(request);
    setError(null);
    setPartial(false);
    try {
      const result = await submitRun(request, previewRef.current);
      if (result.http === 200) {
        setPhase("needs_clarification");
        setRunId(null);
        setQueued(false);
        setTask(null);
        setGaps(result.body.gaps);
        setMessages((prev) => [
          ...prev,
          { id: nextId(seq), role: "assistant", body: gapText(result.body.gaps) },
        ]);
        return;
      }
      if (result.http === 202) {
        setPhase("in_progress");
        setRunId(result.body.run_id);
        setQueued(true);
        setTask(null);
        setGaps([]);
        setAssumptions([]);
        return;
      }
      setPhase("error");
      setRunId(result.body.error.run_id);
      setQueued(false);
      setTask(null);
      setGaps([]);
      setError(result.body.error);
      setMessages((prev) => [
        ...prev,
        {
          id: nextId(seq),
          role: "assistant",
          body: `${result.body.error.code}: ${result.body.error.message}`,
        },
      ]);
    } finally {
      setSending(false);
    }
  }

  return {
    draft,
    setDraft,
    preview,
    setPreview,
    phase,
    messages,
    task,
    queued,
    gaps,
    error,
    assumptions,
    partial,
    fieldRef,
    sending,
    submitDraft(request: RunRequest, pastedSummary: string) {
      const text = pastedSummary || requestSummary(request);
      void send(request, text);
    },
    runAnyway() {
      if (!lastRequest) return;
      void send({ ...lastRequest, confirm_run_anyway: true }, "Run anyway");
    },
    retry() {
      if (!lastRequest) return;
      void send(lastRequest, "Retry the same requisition.");
    },
    edit() {
      fieldRef.current?.focus();
    },
  };
}

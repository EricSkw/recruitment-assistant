import type { ErrorBody, Gap, TaskId } from "../types";
import { TASK_LABELS } from "../types";

export type Phase = "empty" | "needs_clarification" | "in_progress" | "error" | "completed";

type Props = {
  phase: Phase;
  task: TaskId | null;
  queued: boolean;
  gaps: Gap[];
  error: ErrorBody | null;
  assumptions: string[];
  partial: boolean;
  onRunAnyway: () => void;
  onRetry: () => void;
  onEdit: () => void;
  runAnywayEnabled: boolean;
  actionsEnabled: boolean;
};

export function RunStatus({
  phase,
  task,
  queued,
  gaps,
  error,
  assumptions,
  partial,
  onRunAnyway,
  onRetry,
  onEdit,
  runAnywayEnabled,
  actionsEnabled,
}: Props) {
  const taskLine =
    phase === "in_progress"
      ? queued || !task
        ? "Queued. The crew has not finished a task yet."
        : `Running ${task} — ${TASK_LABELS[task]}.`
      : null;

  return (
    <section className="status" aria-live="polite" data-testid="run-status">
      {phase === "empty" ? <p>No run yet.</p> : null}
      {phase === "needs_clarification" ? (
        <div>
          <p>Needs clarification. The crew has not started.</p>
          <ul>
            {gaps.map((gap) => (
              <li key={gap.field}>
                {gap.field}: {gap.reason}{" "}
                {gap.run_anyway_allowed
                  ? "Run anyway is allowed."
                  : "Run anyway is not allowed."}
              </li>
            ))}
          </ul>
          {runAnywayEnabled ? (
            <button type="button" onClick={onRunAnyway} disabled={!actionsEnabled}>
              Run anyway
            </button>
          ) : (
            <p>Add the missing title or must-have skills. Run anyway cannot skip those.</p>
          )}
        </div>
      ) : null}
      {taskLine ? <p data-testid="task-label">{taskLine}</p> : null}
      {phase === "error" && error ? (
        <div id="composer-error" className="error" role="alert">
          <p>
            {error.code}: {error.message}
          </p>
          <div className="report-actions">
            <button type="button" onClick={onRetry} disabled={!actionsEnabled}>
              Retry
            </button>
            <button type="button" onClick={onEdit}>
              Edit requisition
            </button>
          </div>
        </div>
      ) : null}
      {phase === "completed" ? (
        <div>
          <p>{partial ? "Partial result. Review the labeled text before using it." : "Completed."}</p>
          {error ? (
            <p className="error">
              {error.code}: {error.message}
            </p>
          ) : null}
          {assumptions.length > 0 ? (
            <div>
              <p>Assumptions</p>
              <ul>
                {assumptions.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

import type { Dispatch, FormEvent, KeyboardEvent, MutableRefObject, SetStateAction } from "react";
import { draftToRequest, exampleDraft, type Draft } from "../draft";

type Props = {
  draft: Draft;
  disabled: boolean;
  errorDescribedBy: string | undefined;
  fieldRef: MutableRefObject<HTMLInputElement | HTMLTextAreaElement | null>;
  onDraft: Dispatch<SetStateAction<Draft>>;
  onSubmit: (request: ReturnType<typeof draftToRequest>, summary: string) => void;
};

export function Composer({
  draft,
  disabled,
  errorDescribedBy,
  fieldRef,
  onDraft,
  onSubmit,
}: Props) {
  function update(patch: Partial<Draft>) {
    onDraft((current) => ({ ...current, ...patch }));
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (disabled) return;
    const request = draftToRequest(draft);
    const summary =
      draft.mode === "paste" ? draft.raw_blob || "(empty paste)" : undefined;
    onSubmit(request, summary ?? "");
  }

  function onKeyDown(event: KeyboardEvent<HTMLFormElement>) {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      event.currentTarget.requestSubmit();
    }
  }

  return (
    <form className="composer" onSubmit={submit} onKeyDown={onKeyDown} aria-describedby={errorDescribedBy}>
      <fieldset className="mode">
        <legend>Requisition</legend>
        <label>
          <input
            type="radio"
            name="intake-mode"
            checked={draft.mode === "fields"}
            onChange={() => update({ mode: "fields" })}
          />
          Fields
        </label>
        <label>
          <input
            type="radio"
            name="intake-mode"
            checked={draft.mode === "paste"}
            onChange={() => update({ mode: "paste" })}
          />
          Paste YAML
        </label>
      </fieldset>

      {draft.mode === "fields" ? (
        <div className="fields">
          <label>
            Title
            <input
              ref={(node) => {
                if (node) fieldRef.current = node;
              }}
              value={draft.title}
              onChange={(event) => update({ title: event.target.value })}
              required={false}
            />
          </label>
          <label>
            Must-have skills
            <textarea
              value={draft.requirements}
              onChange={(event) => update({ requirements: event.target.value })}
              rows={3}
            />
          </label>
          <label>
            Description
            <textarea
              value={draft.description}
              onChange={(event) => update({ description: event.target.value })}
              rows={3}
            />
          </label>
          <label>
            Responsibilities
            <textarea
              value={draft.responsibilities}
              onChange={(event) => update({ responsibilities: event.target.value })}
              rows={3}
            />
          </label>
          <label>
            Preferred qualifications
            <textarea
              value={draft.preferred_qualifications}
              onChange={(event) => update({ preferred_qualifications: event.target.value })}
              rows={2}
            />
          </label>
          <label>
            Location
            <input value={draft.location} onChange={(event) => update({ location: event.target.value })} />
          </label>
          <label>
            Remote
            <select
              value={draft.remote}
              onChange={(event) => update({ remote: event.target.value as Draft["remote"] })}
            >
              <option value="">Not specified</option>
              <option value="onsite">Onsite</option>
              <option value="hybrid">Hybrid</option>
              <option value="remote">Remote</option>
            </select>
          </label>
          <label>
            Perks and benefits
            <textarea
              value={draft.perks_and_benefits}
              onChange={(event) => update({ perks_and_benefits: event.target.value })}
              rows={2}
            />
          </label>
        </div>
      ) : (
        <label>
          YAML or markdown blob
          <textarea
            ref={(node) => {
              if (node) fieldRef.current = node;
            }}
            value={draft.raw_blob}
            onChange={(event) => update({ raw_blob: event.target.value })}
            rows={10}
            placeholder={"title: Senior Backend Engineer\nrequirements: Python FastAPI PostgreSQL\nlocation: Lisbon\nremote: hybrid"}
          />
        </label>
      )}

      <label>
        Candidate count (5–10)
        <input
          type="number"
          min={5}
          max={10}
          step={1}
          value={draft.candidate_limit}
          onChange={(event) => update({ candidate_limit: event.target.value })}
        />
      </label>

      <div className="composer-actions">
        <button type="submit" disabled={disabled}>
          Send
        </button>
        <button type="button" onClick={() => onDraft(exampleDraft())}>
          Fill example requisition
        </button>
      </div>
      <p className="hint">Ctrl+Enter or Cmd+Enter sends. The requisition stays in the form after an error.</p>
    </form>
  );
}

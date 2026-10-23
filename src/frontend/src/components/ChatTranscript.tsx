import { useState } from "react";
import { MarkdownReport } from "./MarkdownReport";

export type TranscriptItem = {
  id: string;
  role: "user" | "assistant";
  body: string;
  markdown?: string;
  partial?: boolean;
  runId?: string;
};

async function copyText(markdown: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(markdown);
    return true;
  } catch {
    return false;
  }
}

function downloadMarkdown(markdown: string, runId: string): void {
  const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `report-${runId}.md`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function ReportActions({ markdown, runId }: { markdown: string; runId: string }) {
  const [note, setNote] = useState("");
  return (
    <div className="report-actions">
      <button
        type="button"
        onClick={() => {
          void copyText(markdown).then((ok) => {
            setNote(ok ? "Copied." : "Copy failed. Use download.");
          });
        }}
      >
        Copy
      </button>
      <button type="button" onClick={() => downloadMarkdown(markdown, runId)}>
        Download .md
      </button>
      {note ? <span className="inline-note">{note}</span> : null}
    </div>
  );
}

export function ChatTranscript({ items }: { items: TranscriptItem[] }) {
  return (
    <section className="transcript" aria-label="Conversation">
      <h2>Conversation</h2>
      {items.length === 0 ? (
        <p className="empty" data-testid="empty-state">
          Paste a requisition or fill in the fields, then send. The assistant lists missing title,
          must-have skills, seniority, or location before any run starts.
        </p>
      ) : (
        <ol className="messages">
          {items.map((item) => (
            <li key={item.id} className={item.role === "user" ? "message user" : "message assistant"}>
              <span className="who">{item.role === "user" ? "You" : "Assistant"}</span>
              {item.partial ? <strong className="partial-flag">Partial result</strong> : null}
              {item.body ? <p className="body">{item.body}</p> : null}
              {item.markdown ? <MarkdownReport markdown={item.markdown} /> : null}
              {item.markdown && item.runId ? (
                <ReportActions markdown={item.markdown} runId={item.runId} />
              ) : null}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

import { REVIEW_NOTICE } from "./types";
import { ChatTranscript } from "./components/ChatTranscript";
import { Composer } from "./components/Composer";
import { RunStatus } from "./components/RunStatus";
import { useChatSession } from "./session/useChatSession";

export function App() {
  const chat = useChatSession();
  const draft = chat.draft;
  const runAnywayEnabled = chat.gaps.length > 0 && chat.gaps.every((gap) => gap.run_anyway_allowed);
  const busy = chat.phase === "in_progress" || chat.sending;

  return (
    <>
      <header className="banner">
        <h1>Recruitment Assistant</h1>
        <p>{REVIEW_NOTICE}</p>
      </header>
      <main>
        <ChatTranscript items={chat.messages} />
        <RunStatus
          phase={chat.phase}
          task={chat.task}
          queued={chat.queued}
          gaps={chat.gaps}
          error={chat.error}
          assumptions={chat.assumptions}
          partial={chat.partial}
          onRunAnyway={chat.runAnyway}
          onRetry={chat.retry}
          onEdit={chat.edit}
          runAnywayEnabled={runAnywayEnabled}
          actionsEnabled={!busy}
        />
        <Composer
          draft={draft}
          disabled={busy}
          errorDescribedBy={chat.phase === "error" ? "composer-error" : undefined}
          fieldRef={chat.fieldRef}
          onDraft={chat.setDraft}
          onSubmit={(request, summary) => chat.submitDraft(request, summary)}
        />
      </main>
      <footer>
        <p>This page sends the requisition to the local API and polls the run. Outreach drafts are never sent.</p>
      </footer>
    </>
  );
}

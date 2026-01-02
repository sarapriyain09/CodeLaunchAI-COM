import type { ChatMessage } from "../api/orchestrator";

type Props = {
  messages: ChatMessage[];
  draft: string;
  onDraftChange: (value: string) => void;
  onSend: () => void;
  isBusy?: boolean;
};

export default function ChatPanel({ messages, draft, onDraftChange, onSend, isBusy }: Props) {
  return (
    <div className="h-full flex flex-col bg-transparent text-[color:var(--text-primary)]">
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 ? (
          <>
            <p className="text-sm text-[color:var(--text-muted)]">
              Describe the website or app you want to build.
            </p>
            <p className="text-xs text-[color:var(--text-muted)]/80">
              Mention pages, sections, integrations, and tone.
            </p>
          </>
        ) : null}

        {messages.map((m, idx) => {
          const isUser = m.role === "user";
          return (
            <div
              key={`${m.role}-${idx}`}
              className={[
                "max-w-[95%] rounded-2xl px-3 py-2 text-sm border",
                isUser
                  ? "ml-auto bg-[color:var(--bg-muted)] text-[color:var(--text-primary)] border-[color:var(--border)]"
                  : "mr-auto bg-[color:var(--panel)] text-[color:var(--text-primary)] border-[color:var(--border)]",
              ].join(" ")}
            >
              <div className="text-[10px] uppercase tracking-wide text-[color:var(--text-muted)]/70 mb-1">
                {isUser ? "You" : "Assistant"}
              </div>
              <div className="whitespace-pre-wrap">{m.content}</div>
            </div>
          );
        })}
      </div>

      <div className="border-t border-[color:var(--border)] p-3">
        <textarea
          className="w-full border border-[color:var(--border)] bg-[color:var(--panel)] rounded-2xl p-3 text-sm text-[color:var(--text-primary)] placeholder:text-[color:var(--text-muted)]"
          rows={6}
          placeholder="e.g. Build a modern ecommerce site with hero, product grid, testimonials..."
          value={draft}
          onChange={(event) => onDraftChange(event.target.value)}
        />

        <div className="mt-2 flex justify-end">
          <button
            className="px-4 py-2 rounded-full text-sm font-semibold disabled:opacity-60 disabled:cursor-not-allowed"
            style={{
              background: "linear-gradient(120deg, var(--accent), var(--accent-secondary))",
              color: "#090b12",
              boxShadow: "0 10px 30px rgba(93, 224, 230, 0.35)",
            }}
            onClick={onSend}
            disabled={isBusy || !draft.trim()}
          >
            {isBusy ? "Thinking…" : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}

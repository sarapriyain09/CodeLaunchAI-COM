type Props = {
  onGenerate: () => void;
  onUpdate?: () => void;
  isBusy?: boolean;
  isGenerateDisabled?: boolean;
  isUpdateDisabled?: boolean;
  projects?: Array<{ id: string; name: string }>;
  activeProjectId?: string | null;
  onSelectProject?: (projectId: string) => void;
  onCreateProject?: () => void;
  onDownload?: () => void;
  isDownloadDisabled?: boolean;
  subscribeHint?: string | null;
};

export default function TopBar({
  onGenerate,
  onUpdate,
  isBusy,
  isGenerateDisabled,
  isUpdateDisabled,
  projects,
  activeProjectId,
  onSelectProject,
  onCreateProject,
  onDownload,
  isDownloadDisabled,
  subscribeHint,
}: Props) {
  return (
    <div className="h-14 border-b border-[color:var(--border)] flex items-center justify-between px-4 bg-[color:var(--panel)]">
      <div>
        <p className="text-xs uppercase tracking-wide text-[color:var(--text-muted)]/70">Project</p>
        <p className="font-semibold text-[color:var(--text-primary)]">CodeLaunchAI Demo</p>
      </div>
      <div className="flex gap-2 items-center">
        {projects && projects.length > 0 && onSelectProject ? (
          <select
            className="h-9 px-3 rounded-full text-sm border border-[color:var(--border)] bg-transparent text-[color:var(--text-primary)]"
            value={activeProjectId ?? ""}
            onChange={(e) => onSelectProject(e.target.value)}
            disabled={isBusy}
          >
            <option value="" disabled>
              Select project
            </option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        ) : null}

        {onCreateProject ? (
          <button
            className="px-4 py-2 rounded-full text-sm font-semibold border border-[color:var(--border)] disabled:opacity-60 disabled:cursor-not-allowed"
            onClick={onCreateProject}
            disabled={isBusy}
          >
            New
          </button>
        ) : null}

        {onDownload ? (
          <div className="flex items-center gap-2">
            <button
              className="px-4 py-2 rounded-full text-sm font-semibold border border-[color:var(--border)] disabled:opacity-60 disabled:cursor-not-allowed"
              onClick={onDownload}
              disabled={isBusy || isDownloadDisabled}
            >
              Download
            </button>
            {subscribeHint ? (
              <span className="text-xs text-[color:var(--text-muted)]/70">{subscribeHint}</span>
            ) : null}
          </div>
        ) : null}

        {onUpdate ? (
          <button
            className="px-4 py-2 rounded-full text-sm font-semibold border border-[color:var(--border)] disabled:opacity-60 disabled:cursor-not-allowed"
            onClick={onUpdate}
            disabled={isBusy || isUpdateDisabled}
            title="Update the existing app (incremental)"
          >
            Update
          </button>
        ) : null}

        <button
          className="px-4 py-2 rounded-full text-sm font-semibold disabled:opacity-60 disabled:cursor-not-allowed"
          style={{
            background: "linear-gradient(120deg, var(--accent), var(--accent-secondary))",
            color: "#090b12",
            boxShadow: "0 10px 30px rgba(93, 224, 230, 0.35)",
          }}
          onClick={onGenerate}
          disabled={isBusy || isGenerateDisabled}
        >
          {isBusy ? "Working…" : "Generate"}
        </button>
      </div>
    </div>
  );
}

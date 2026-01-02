import Editor from "@monaco-editor/react";

function guessLanguage(path: string) {
  const lower = path.toLowerCase();
  if (lower.endsWith(".tsx") || lower.endsWith(".ts")) return "typescript";
  if (lower.endsWith(".jsx") || lower.endsWith(".js")) return "javascript";
  if (lower.endsWith(".json")) return "json";
  if (lower.endsWith(".css")) return "css";
  if (lower.endsWith(".html")) return "html";
  if (lower.endsWith(".md")) return "markdown";
  return "plaintext";
}

type Props = {
  path: string;
  value: string;
  readOnly?: boolean;
  onChange?: (value: string) => void;
};

export default function CodeEditor({ path, value, readOnly = true, onChange }: Props) {
  const language = guessLanguage(path);

  return (
    <div className="h-full flex flex-col bg-transparent">
      <div className="px-3 py-2 border-b border-[color:var(--border)] text-xs text-[color:var(--text-muted)] flex items-center justify-between">
        <span className="truncate" title={path}>
          {path}
        </span>
        <span className="text-[color:var(--text-muted)]/70">{readOnly ? "Read-only" : "Editable"}</span>
      </div>

      <div className="flex-1">
        <Editor
          height="100%"
          language={language}
          theme="vs-dark"
          value={value}
          onChange={(nextValue) => onChange?.(nextValue ?? "")}
          options={{
            readOnly,
            minimap: { enabled: false },
            fontSize: 13,
            wordWrap: "on",
            scrollBeyondLastLine: false,
            automaticLayout: true,
            smoothScrolling: true,
          }}
        />
      </div>
    </div>
  );
}

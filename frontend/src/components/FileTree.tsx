type Props = {
  files: { path: string }[];
  selectedPath: string;
  onSelect: (path: string) => void;
};

export default function FileTree({ files, selectedPath, onSelect }: Props) {
  return (
    <div className="p-3 border-b border-[color:var(--border)] bg-transparent">
      <h3 className="text-sm font-semibold mb-2 text-[color:var(--text-primary)]">Files</h3>

      <div className="space-y-1">
        {files.map((file) => {
          const active = file.path === selectedPath;
          return (
            <button
              key={file.path}
              onClick={() => onSelect(file.path)}
              className={[
                "w-full text-left text-sm px-2 py-1 rounded-lg transition",
                active
                  ? "bg-[color:var(--bg-muted)] text-[color:var(--text-primary)]"
                  : "hover:bg-[color:var(--bg-muted)]/70 text-[color:var(--text-muted)]",
              ].join(" ")}
              title={file.path}
            >
              📄 {file.path}
            </button>
          );
        })}
      </div>
    </div>
  );
}

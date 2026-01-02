import { useEffect, useRef, useState } from "react";

type Props = {
  streamUrl?: string | null;
  onDone?: (previewPathOrUrl?: string) => void;
  onError?: (message: string) => void;
};

export default function BuildLogs({ streamUrl, onDone, onError }: Props) {
  const [logs, setLogs] = useState<string[]>([]);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;

    if (!streamUrl) {
      return;
    }

    setLogs([`--- build stream: ${streamUrl} ---`]);

    const source = new EventSource(streamUrl);
    eventSourceRef.current = source;

    source.addEventListener("status", (event) => {
      const data = (event as MessageEvent).data;
      setLogs((prev) => [...prev, `[status] ${data}`]);
    });

    source.addEventListener("log", (event) => {
      const data = (event as MessageEvent).data;
      setLogs((prev) => [...prev, data]);
    });

    source.addEventListener("done", (event) => {
      const data = (event as MessageEvent).data;
      setLogs((prev) => [...prev, `✅ Done: ${data}`]);
      onDone?.(data);
      source.close();
      eventSourceRef.current = null;
    });

    source.addEventListener("error", (event) => {
      const message = (event as MessageEvent).data || "Build stream error";
      setLogs((prev) => [...prev, `❌ ${message}`]);
      onError?.(String(message));
      source.close();
      eventSourceRef.current = null;
    });

    return () => {
      source.close();
    };
  }, [streamUrl, onDone, onError]);

  return (
    <div className="p-3 text-xs bg-black text-green-400 h-48 overflow-y-auto font-mono space-y-1">
      {logs.length === 0 && <div>Waiting for build logs…</div>}
      {logs.map((line, index) => (
        <div key={`${line}-${index}`} className="whitespace-pre-wrap">
          {line}
        </div>
      ))}
    </div>
  );
}

import { useCallback, useEffect, useMemo, useState } from "react";
import TopBar from "../components/TopBar";
import ChatPanel from "../components/ChatPanel";
import PreviewPane from "../components/PreviewPane";
import FileTree from "../components/FileTree";
import CodeEditor from "../components/CodeEditor";
import { useProjectFiles } from "../state/useProjectFiles";
import * as api from "../api/orchestrator";

const PROJECT_NAME = "generated-app";

function getActiveSessionProjectId() {
  return sessionStorage.getItem("cla_active_project_id")
    || sessionStorage.getItem("cla_project_id");
}

function setActiveSessionProjectId(id: string) {
  sessionStorage.setItem("cla_active_project_id", id);
  // Back-compat with older sessions.
  sessionStorage.setItem("cla_project_id", id);
}

export default function Workspace() {
  const { files, setFiles, selectedFile, selectedPath, setSelectedPath } = useProjectFiles();
  const [projects, setProjects] = useState<api.Project[]>([]);
  const [projectId, setProjectId] = useState<string | null>(() => getActiveSessionProjectId());
  const [downloadStatus, setDownloadStatus] = useState<string | null>(null);
  const [leftTab, setLeftTab] = useState<"chat" | "blueprint">("chat");
  const [rightTab, setRightTab] = useState<"preview" | "code">("preview");
  const [projectState, setProjectState] = useState<api.ProjectState | null>(null);
  const [projectStateError, setProjectStateError] = useState<string | null>(null);
  const [chatMessages, setChatMessages] = useState<api.ChatMessage[]>([
    {
      role: "assistant",
      content:
        "Tell me what you want to build. I’ll ask a couple of clarifying questions, then you can click Generate.",
    },
  ]);
  const [draft, setDraft] = useState(
    "Build a modern minimal jewellery ecommerce site with home, product grid, product detail, about, and contact sections.",
  );
  const [isBusy, setIsBusy] = useState(false);
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [blueprintMeta, setBlueprintMeta] = useState<string | null>(null);

  const redirectToPricing = useCallback(() => {
    // HashRouter: route to landing (/) and include a query that Landing will use to scroll.
    // Results in: /app/#/?scroll=pricing
    window.location.hash = "/?scroll=pricing";
  }, []);

  const refreshProjectState = useCallback(async () => {
    if (!projectId) return;
    try {
      setProjectStateError(null);
      const state = await api.getProjectState(projectId);
      setProjectState(state);
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      setProjectState(null);
      setProjectStateError(message);
    }
  }, [projectId]);

  async function doDownloadZip(token: string) {
    if (!projectId) return;
    setDownloadStatus("Preparing download…");
    try {
      const blob = await api.exportZip(projectId, token);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${projectId}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setDownloadStatus("Download started");
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      if (message.includes("HTTP 401")) {
        setDownloadStatus("Registration required to download. Redirecting to Pricing…");
        redirectToPricing();
      } else if (message.includes("HTTP 402")) {
        setDownloadStatus("Subscription required to download. Redirecting to Pricing…");
        redirectToPricing();
      } else {
        setDownloadStatus(`Download error: ${message}`);
      }
    }
  }

  // Load projects list and ensure we have an active project.
  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const list = await api.listProjects();
        if (cancelled) return;
        setProjects(list.projects);

        const active = projectId;
        if (active) {
          const exists = list.projects.some((p) => p.id === active);
          if (!exists) {
            const created = await api.createProject(undefined, active);
            if (cancelled) return;
            setProjects((prev) => [created, ...prev]);
          }
          setPreviewUrl(api.previewUrl(active));
          return;
        }

        const created = await api.createProject();
        if (cancelled) return;
        setProjects((prev) => [created, ...prev]);
        setProjectId(created.id);
        setActiveSessionProjectId(created.id);
        setPreviewUrl(api.previewUrl(created.id));
      } catch {
        // Non-fatal: workspace can still operate with an existing session project id.
        if (!cancelled && projectId) {
          setPreviewUrl(api.previewUrl(projectId));
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const subscribeHint = null;

  // Keep preview URL aligned when project changes.
  useEffect(() => {
    if (!projectId) return;
    setPreviewUrl(api.previewUrl(projectId));
  }, [projectId]);

  // Load persisted chat history when project changes.
  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;

    (async () => {
      try {
        const resp = await api.getProjectChatHistory(projectId);
        if (cancelled) return;
        const msgs = resp.messages.map((m) => ({ role: m.role, content: m.content })) as api.ChatMessage[];
        setChatMessages(
          msgs.length
            ? msgs
            : [
                {
                  role: "assistant",
                  content:
                    "Tell me what you want to build. I’ll ask a couple of clarifying questions, then you can click Generate.",
                },
              ],
        );
      } catch {
        // Non-fatal: keep local-only chat.
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [projectId]);

  // Load persisted generated files when project changes (best-effort).
  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;

    (async () => {
      try {
        const resp = await api.getProjectFiles(projectId);
        if (cancelled) return;
        if (Array.isArray(resp.files) && resp.files.length > 0) {
          setFiles(resp.files);
        }
      } catch {
        // Non-fatal: file persistence is optional.
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [projectId, setFiles]);

  const goal = useMemo(() => {
    // Use the latest user message as the goal for planning.
    const lastUser = [...chatMessages].reverse().find((m) => m.role === "user");
    return lastUser?.content ?? draft;
  }, [chatMessages, draft]);

  async function handleGenerate() {
    if (!goal.trim()) return;
    if (!projectId) return;

    setIsBusy(true);
    setStreamUrl(null);

    try {
      const planResponse = await api.plan(goal.trim());
      const routeCount = (planResponse.blueprint as any)?.routes?.length ?? 0;
      setBlueprintMeta(`Blueprint ready (routes: ${routeCount})`);

      await api.putProjectState(projectId, {
        blueprint: planResponse.blueprint as Record<string, unknown>,
        plan: {
          goal: goal.trim(),
          meta: (planResponse as any)?.meta ?? null,
        },
      });
      if (leftTab === "blueprint") {
        await refreshProjectState();
      }

      const filesResponse = await api.generateFiles(planResponse.blueprint, PROJECT_NAME);
      setFiles(filesResponse.files);

      // Persist generated file tree/content for this project (best-effort).
      try {
        await api.putProjectFiles(projectId, filesResponse.files);
      } catch {
        // Non-fatal: generation/preview should still proceed.
      }

      await api.materialize(projectId, planResponse.blueprint, PROJECT_NAME);

      const url = api.buildStreamUrl(projectId, true);
      setStreamUrl(url);
      setBlueprintMeta("Building preview…");
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setBlueprintMeta(`Error: ${message}`);
    } finally {
      setIsBusy(false);
    }
  }

  const handleBuildDone = useCallback((pathOrUrl?: string) => {
    if (!projectId) return;
    const candidate = pathOrUrl && pathOrUrl.startsWith("http")
      ? pathOrUrl
      : api.previewUrl(projectId);
    const next = `${candidate}${candidate.includes("?") ? "&" : "?"}t=${Date.now()}`;
    setPreviewUrl(next);
  }, [projectId]);

  // Consume the build stream in the background so we can keep a clean 2-pane UI.
  useEffect(() => {
    if (!streamUrl) return;

    const source = new EventSource(streamUrl);

    source.addEventListener("status", (event) => {
      const data = (event as MessageEvent).data;
      if (typeof data === "string" && data && data !== "ping") {
        setBlueprintMeta(String(data));
      }
    });

    source.addEventListener("done", (event) => {
      const data = (event as MessageEvent).data;
      handleBuildDone(typeof data === "string" ? data : undefined);
      setBlueprintMeta("Preview ready");
      source.close();
      setStreamUrl(null);
    });

    source.addEventListener("error", (event) => {
      const message = (event as MessageEvent).data || "Build stream error";
      setBlueprintMeta(`Error: ${String(message)}`);
      source.close();
      setStreamUrl(null);
    });

    return () => source.close();
  }, [streamUrl, handleBuildDone]);

  return (
    <div className="h-screen flex flex-col bg-transparent text-[color:var(--text-primary)]">
      <TopBar
        onGenerate={handleGenerate}
        isBusy={isBusy}
        isGenerateDisabled={!projectId}
        subscribeHint={subscribeHint}
        onDownload={async () => {
          if (!projectId) return;
          setDownloadStatus(null);
          const token = api.getAccessToken();
          if (!token) {
            setDownloadStatus("Registration required to download. Redirecting to Pricing…");
            redirectToPricing();
            return;
          }
          await doDownloadZip(token);
        }}
        isDownloadDisabled={!projectId}
        projects={projects}
        activeProjectId={projectId}
        onSelectProject={(id) => {
          setProjectId(id);
          setActiveSessionProjectId(id);
          setFiles([]);
          setBlueprintMeta(null);
          setStreamUrl(null);
          setPreviewUrl(api.previewUrl(id));
          setDownloadStatus(null);
          setProjectState(null);
          setProjectStateError(null);
        }}
        onCreateProject={async () => {
          if (isBusy) return;
          setIsBusy(true);
          try {
            const created = await api.createProject();
            setProjects((prev) => [created, ...prev]);
            setProjectId(created.id);
            setActiveSessionProjectId(created.id);
            setFiles([]);
            setBlueprintMeta(null);
            setStreamUrl(null);
            setPreviewUrl(api.previewUrl(created.id));
            setDownloadStatus(null);
          } finally {
            setIsBusy(false);
          }
        }}
      />

      <div className="flex flex-1 overflow-hidden">
        <div className="w-[300px] shrink-0 border-r border-[color:var(--border)] bg-[color:var(--panel)]">
          <div className="h-full flex flex-col">
            <div className="border-b border-[color:var(--border)] px-2 py-2 flex gap-2">
              <button
                className={[
                  "px-3 py-1.5 rounded-full text-xs font-semibold border",
                  leftTab === "chat"
                    ? "bg-[color:var(--bg-muted)] border-[color:var(--border)]"
                    : "bg-transparent border-[color:var(--border)] opacity-80",
                ].join(" ")}
                onClick={() => setLeftTab("chat")}
              >
                Chat
              </button>
              <button
                className={[
                  "px-3 py-1.5 rounded-full text-xs font-semibold border",
                  leftTab === "blueprint"
                    ? "bg-[color:var(--bg-muted)] border-[color:var(--border)]"
                    : "bg-transparent border-[color:var(--border)] opacity-80",
                ].join(" ")}
                onClick={async () => {
                  setLeftTab("blueprint");
                  await refreshProjectState();
                }}
              >
                Blueprint
              </button>
            </div>

            {leftTab === "chat" ? (
              <ChatPanel
                messages={chatMessages}
                draft={draft}
                onDraftChange={setDraft}
                isBusy={isBusy}
                onSend={async () => {
                  const text = draft.trim();
                  if (!text) return;
                  if (!projectId) return;
                  setIsBusy(true);
                  setBlueprintMeta(null);
                  setChatMessages((prev) => [...prev, { role: "user", content: text }]);
                  setDraft("");
                  try {
                    const resp = await api.projectChat(projectId, text);
                    setChatMessages((prev) => [...prev, { role: "assistant", content: resp.reply }]);
                  } catch (error) {
                    const message = error instanceof Error ? error.message : String(error);
                    setChatMessages((prev) => [
                      ...prev,
                      { role: "assistant", content: `Error: ${message}` },
                    ]);
                  } finally {
                    setIsBusy(false);
                  }
                }}
              />
            ) : (
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                <div className="text-xs text-[color:var(--text-muted)]/80">
                  Stored blueprint/plan JSON for this project.
                </div>
                {projectStateError ? (
                  <div className="text-sm text-red-400">{projectStateError}</div>
                ) : null}
                <div>
                  <div className="text-xs uppercase tracking-wide text-[color:var(--text-muted)]/70 mb-2">
                    Blueprint
                  </div>
                  <pre className="text-xs whitespace-pre-wrap break-words bg-[color:var(--bg-muted)] border border-[color:var(--border)] rounded-xl p-3">
                    {JSON.stringify(projectState?.blueprint ?? {}, null, 2)}
                  </pre>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-[color:var(--text-muted)]/70 mb-2">
                    Plan
                  </div>
                  <pre className="text-xs whitespace-pre-wrap break-words bg-[color:var(--bg-muted)] border border-[color:var(--border)] rounded-xl p-3">
                    {JSON.stringify(projectState?.plan ?? {}, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="flex-1 bg-[color:var(--panel)]">
          <div className="h-full flex flex-col">
            <div className="border-b border-[color:var(--border)] px-2 py-2 flex gap-2 items-center justify-between">
              <div className="flex gap-2">
                <button
                  className={[
                    "px-3 py-1.5 rounded-full text-xs font-semibold border",
                    rightTab === "preview"
                      ? "bg-[color:var(--bg-muted)] border-[color:var(--border)]"
                      : "bg-transparent border-[color:var(--border)] opacity-80",
                  ].join(" ")}
                  onClick={() => setRightTab("preview")}
                >
                  Preview
                </button>
                <button
                  className={[
                    "px-3 py-1.5 rounded-full text-xs font-semibold border",
                    rightTab === "code"
                      ? "bg-[color:var(--bg-muted)] border-[color:var(--border)]"
                      : "bg-transparent border-[color:var(--border)] opacity-80",
                  ].join(" ")}
                  onClick={() => setRightTab("code")}
                >
                  Code
                </button>
              </div>

              {rightTab === "code" ? (
                <div className="text-xs text-[color:var(--text-muted)]/70">
                  {files.length ? `${files.length} files` : "No files yet — click Generate"}
                </div>
              ) : null}
            </div>

            <div className="flex-1 min-h-0">
              {rightTab === "preview" ? (
                <PreviewPane url={previewUrl} />
              ) : (
                <div className="h-full flex">
                  <div className="w-[320px] shrink-0 border-r border-[color:var(--border)] overflow-y-auto">
                    <FileTree
                      files={files}
                      selectedPath={selectedPath}
                      onSelect={(path) => setSelectedPath(path)}
                    />
                  </div>
                  <div className="flex-1 min-w-0">
                    {selectedFile ? (
                      <CodeEditor path={selectedFile.path} value={selectedFile.content} readOnly />
                    ) : (
                      <div className="h-full flex items-center justify-center text-sm text-[color:var(--text-muted)]">
                        Select a file to view its contents.
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {blueprintMeta || downloadStatus ? (
        <div className="border-t border-[color:var(--border)] bg-[color:var(--panel)] text-xs text-[color:var(--text-muted)] px-4 py-2">
          {downloadStatus ? <span className="mr-3">{downloadStatus}</span> : null}
          {blueprintMeta ? <span>{blueprintMeta}</span> : null}
        </div>
      ) : null}
    </div>
  );
}

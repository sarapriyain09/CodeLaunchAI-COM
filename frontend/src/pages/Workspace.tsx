import { useCallback, useEffect, useMemo, useState } from "react";
import "./chat-layout.css";
import { useProjectFiles } from "../state/useProjectFiles";
import * as api from "../api/orchestrator";

const PROJECT_NAME = "generated-app";

function getActiveSessionProjectId() {
  return sessionStorage.getItem("cla_active_project_id") || sessionStorage.getItem("cla_project_id");
}

function setActiveSessionProjectId(id: string) {
  sessionStorage.setItem("cla_active_project_id", id);
  // Back-compat with older sessions.
  sessionStorage.setItem("cla_project_id", id);
}

function formatProjectTimestamp(iso?: string | null) {
  if (!iso) return "Just now";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "Just now";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export default function Workspace() {
  const { setFiles } = useProjectFiles();
  const [projects, setProjects] = useState<api.Project[]>([]);
  const [projectId, setProjectId] = useState<string | null>(() => getActiveSessionProjectId());
  const [downloadStatus, setDownloadStatus] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [threadQuery, setThreadQuery] = useState("");
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

  const filteredProjects = useMemo(() => {
    const q = threadQuery.trim().toLowerCase();
    if (!q) return projects;
    return projects.filter((project) => {
      const name = project.name?.toLowerCase() ?? "";
      return name.includes(q) || project.id.toLowerCase().includes(q);
    });
  }, [projects, threadQuery]);

  const activeProject = useMemo(
    () => (projectId ? projects.find((project) => project.id === projectId) ?? null : null),
    [projects, projectId],
  );

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

  function handleSelectProject(id: string) {
    setProjectId(id);
    setActiveSessionProjectId(id);
    setFiles([]);
    setBlueprintMeta(null);
    setStreamUrl(null);
    setPreviewUrl(api.previewUrl(id));
    setDownloadStatus(null);
  }

  async function handleCreateProject() {
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
  }

  async function handleDownloadClick() {
    if (!projectId) return;
    setDownloadStatus(null);
    const token = api.getAccessToken();
    if (!token) {
      setDownloadStatus("Registration required to download. Redirecting to Pricing…");
      redirectToPricing();
      return;
    }
    await doDownloadZip(token);
  }

  function handlePreviewClick() {
    if (!previewUrl) return;
    window.open(previewUrl, "_blank", "noopener,noreferrer");
  }

  async function handleSend() {
    const text = draft.trim();
    if (!text || !projectId) return;
    setIsBusy(true);
    setBlueprintMeta(null);
    setChatMessages((prev) => [...prev, { role: "user", content: text }]);
    setDraft("");
    try {
      const resp = await api.projectChat(projectId, text);
      setChatMessages((prev) => [...prev, { role: "assistant", content: resp.reply }]);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setChatMessages((prev) => [...prev, { role: "assistant", content: `Error: ${message}` }]);
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

  const subtitleText = blueprintMeta ?? (isBusy ? "Builder is thinking…" : "Describe what you want to build.");
  const hintText = downloadStatus ?? "Shift+Enter for a new line. Generate to refresh the preview.";
  const disableSend = !draft.trim() || !projectId || isBusy;
  const disableGenerate = !projectId || !goal.trim() || isBusy;
  const disableDownload = !projectId || isBusy;
  const disablePreview = !previewUrl;

  return (
    <div className="chatLayoutScreen">
      <div className="appShell">
        <aside className={`sidebar ${sidebarOpen ? "" : "collapsed"}`}>
          <div className="sidebarTop">
            <button className="iconBtn" onClick={() => setSidebarOpen((prev) => !prev)} aria-label="Toggle sidebar">
              ☰
            </button>
            <div className="brand">
              <div className="logo" aria-hidden="true" />
              <span>CodeLaunch Builder</span>
            </div>
          </div>

          <div className="sidebarActions">
            <button className="primaryBtn" onClick={() => void handleCreateProject()} disabled={isBusy}>
              + New chat
            </button>
            <div className="searchWrap">
              <input
                className="search"
                placeholder="Search workspaces..."
                value={threadQuery}
                onChange={(event) => setThreadQuery(event.target.value)}
              />
            </div>
          </div>

          <div className="threadList">
            {filteredProjects.length === 0 ? (
              <div className="thread">
                <div className="threadTitle">No matches</div>
                <div className="threadMeta">Adjust your search.</div>
              </div>
            ) : (
              filteredProjects.map((project) => (
                <button
                  key={project.id}
                  className={`thread ${project.id === projectId ? "active" : ""}`}
                  onClick={() => handleSelectProject(project.id)}
                >
                  <div className="threadTitle">{project.name || "Untitled project"}</div>
                  <div className="threadMeta">{formatProjectTimestamp(project.updated_at)}</div>
                </button>
              ))
            )}
          </div>

          <div className="sidebarFooter">
            <div className="userChip">
              <div className="avatar" aria-hidden="true">
                {(activeProject?.name ?? "CL").slice(0, 1).toUpperCase()}
              </div>
              <div className="userText">
                <div className="userName">{activeProject?.name || "Workspace"}</div>
                <div className="userMeta">{activeProject ? "Live project" : "Creating project"}</div>
              </div>
            </div>
          </div>
        </aside>

        <main className="main">
          <header className="topbar">
            <button className="iconBtn mobileOnly" onClick={() => setSidebarOpen(true)} aria-label="Open sidebar">
              ☰
            </button>
            <div className="topbarTitle">
              <div className="title">{activeProject?.name || "Untitled project"}</div>
              <div className="subtitle">{subtitleText}</div>
            </div>
            <div className="topbarRight">
              <button className="ghostBtn" onClick={handlePreviewClick} disabled={disablePreview}>
                Open preview
              </button>
              <button className="ghostBtn" onClick={() => void handleDownloadClick()} disabled={disableDownload}>
                Download
              </button>
              <button className="ghostBtn" onClick={() => void handleGenerate()} disabled={disableGenerate}>
                {isBusy ? "Working…" : "Generate"}
              </button>
            </div>
          </header>

          <section className="chatArea">
            <div className="messages">
              {chatMessages.map((message, index) => (
                <div key={`${message.role}-${index}`} className={`row ${message.role === "user" ? "me" : "bot"}`}>
                  <div className="bubble">
                    <div className="role">{message.role === "user" ? "You" : "Assistant"}</div>
                    <div className="text">{message.content}</div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <footer className="composerWrap">
            <div className="composer">
              <textarea
                className="input"
                placeholder="Message... (Enter to send, Shift+Enter for new line)"
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    void handleSend();
                  }
                }}
                rows={1}
                disabled={!projectId}
              />
              <button className="sendBtn" onClick={() => void handleSend()} disabled={disableSend}>
                Send
              </button>
            </div>
            <div className="hint">{hintText}</div>
          </footer>
        </main>
      </div>
    </div>
  );
}

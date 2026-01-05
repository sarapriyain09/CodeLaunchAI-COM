import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import "./chat-layout.css";
import { useProjectFiles } from "../state/useProjectFiles";
import * as api from "../api/orchestrator";

const PROJECT_NAME = "generated-app";

const DEFAULT_ASSISTANT_MESSAGE: api.ChatMessage = {
  role: "assistant",
  content:
    "Tell me what you want to build. I’ll ask a couple of clarifying questions, then you can click Generate.",
};

function getActiveSessionProjectId() {
  return (
    sessionStorage.getItem("cla_active_project_id") ||
    sessionStorage.getItem("cla_project_id") ||
    localStorage.getItem("cla_active_project_id") ||
    localStorage.getItem("cla_project_id")
  );
}

function setActiveSessionProjectId(id: string) {
  sessionStorage.setItem("cla_active_project_id", id);
  // Back-compat with older sessions.
  sessionStorage.setItem("cla_project_id", id);

  // Persist across refresh/reopen so we don't auto-create new projects.
  localStorage.setItem("cla_active_project_id", id);
  localStorage.setItem("cla_project_id", id);
}

function clearActiveSessionProjectId() {
  sessionStorage.removeItem("cla_active_project_id");
  sessionStorage.removeItem("cla_project_id");

  localStorage.removeItem("cla_active_project_id");
  localStorage.removeItem("cla_project_id");
}

function formatProjectTimestamp(iso?: string | null) {
  if (!iso) return "Just now";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "Just now";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function parseHttpStatusFromError(error: unknown): number | null {
  const message = error instanceof Error ? error.message : String(error);
  const match = message.match(/\bHTTP\s+(\d{3})\b/);
  if (!match) return null;
  const code = Number(match[1]);
  return Number.isFinite(code) ? code : null;
}

function tryExtractHttpJsonDetail(error: unknown): any | null {
  const message = error instanceof Error ? error.message : String(error);
  const idx = message.indexOf(": ");
  if (idx < 0) return null;
  const tail = message.slice(idx + 2).trim();
  if (!tail.startsWith("{") && !tail.startsWith("[")) return null;
  try {
    return JSON.parse(tail);
  } catch {
    return null;
  }
}

function rateLimitHint(error: unknown): string {
  const payload = tryExtractHttpJsonDetail(error);
  const retry = payload && typeof payload.retry_after_seconds === "number" ? payload.retry_after_seconds : null;
  if (retry && retry > 0) return `You're sending requests too fast. Try again in ~${retry}s.`;
  return "You're sending requests too fast. Please wait a few seconds and try again.";
}

export default function Workspace() {
  const { files, setFiles, selectedPath, setSelectedPath, selectedFile } = useProjectFiles();
  const [projects, setProjects] = useState<api.Project[]>([]);
  const [projectId, setProjectId] = useState<string | null>(() => getActiveSessionProjectId());
  const [downloadStatus, setDownloadStatus] = useState<string | null>(null);
  const [usageStatus, setUsageStatus] = useState<api.UsageStatus | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [threadQuery, setThreadQuery] = useState("");
  const [chatMessages, setChatMessages] = useState<api.ChatMessage[]>([DEFAULT_ASSISTANT_MESSAGE]);
  const [draft, setDraft] = useState(
    "Build a modern minimal jewellery ecommerce site with home, product grid, product detail, about, and contact sections.",
  );
  const [isBusy, setIsBusy] = useState(false);
  const [deletingProjectId, setDeletingProjectId] = useState<string | null>(null);
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [blueprintMeta, setBlueprintMeta] = useState<string | null>(null);
  const [aiOffline, setAiOffline] = useState<{ offline: boolean; reason?: string } | null>(null);
  const [hasPreview, setHasPreview] = useState<boolean | null>(null);
  const [buildProgress, setBuildProgress] = useState<number | null>(null);
  const [showCodePanel, setShowCodePanel] = useState(true);
  const [generationStatus, setGenerationStatus] = useState<string | null>(null);
  const revealTimersRef = useRef<number[]>([]);
  const revealBufferRef = useRef<api.FileItem[]>([]);

  const clearRevealTimers = useCallback(() => {
    for (const id of revealTimersRef.current) {
      window.clearTimeout(id);
    }
    revealTimersRef.current = [];
  }, []);

  const revealFiles = useCallback((nextFiles: api.FileItem[], label: string) => {
    clearRevealTimers();
    revealBufferRef.current = [];
    setGenerationStatus(label);
    setShowCodePanel(true);
    setFiles([]);

    if (!Array.isArray(nextFiles) || nextFiles.length === 0) {
      const doneId = window.setTimeout(() => setGenerationStatus(null), 500);
      revealTimersRef.current.push(doneId);
      return;
    }

    // Lock selection to the first file so the panel has something to show as files arrive.
    setSelectedPath(nextFiles[0].path);

    // Reveal in small batches to create a “generating…” feel (even though backend returns the
    // full file list at once).
    const batchSize = 3;
    const delayMs = 80;
    const total = nextFiles.length;
    const batches = Math.ceil(total / batchSize);

    for (let batch = 0; batch < batches; batch += 1) {
      const id = window.setTimeout(() => {
        const start = batch * batchSize;
        const end = Math.min(total, start + batchSize);
        revealBufferRef.current = revealBufferRef.current.concat(nextFiles.slice(start, end));
        setFiles(revealBufferRef.current);
        setGenerationStatus(`${label} ${end}/${total}`);
      }, batch * delayMs);
      revealTimersRef.current.push(id);
    }

    const doneId = window.setTimeout(() => setGenerationStatus(null), batches * delayMs + 350);
    revealTimersRef.current.push(doneId);
  }, [clearRevealTimers, setFiles, setSelectedPath]);

  useEffect(() => {
    return () => {
      clearRevealTimers();
    };
  }, [clearRevealTimers]);

  function coerceOfflineMeta(meta: unknown): { offline: boolean; reason?: string } | null {
    if (!meta || typeof meta !== "object") return null;
    const m = meta as any;
    if (typeof m.offline !== "boolean") return null;
    const reason = typeof m.reason === "string" && m.reason.trim() ? m.reason.trim() : undefined;
    return { offline: m.offline, reason };
  }

  const checkPreviewAvailable = useCallback(async (candidateUrl: string): Promise<boolean> => {
    try {
      // Prefer HEAD to avoid fetching full HTML.
      const head = await fetch(candidateUrl, { method: "HEAD", cache: "no-store" });
      if (head.ok) return true;
      if (head.status !== 405) return false;
    } catch {
      // Fall through to GET as a best-effort.
    }

    try {
      const resp = await fetch(candidateUrl, { method: "GET", cache: "no-store" });
      return resp.ok;
    } catch {
      return false;
    }
  }, []);

  const redirectToFrontPage = useCallback(() => {
    // Public front page (outside HashRouter).
    window.location.href = "/";
  }, []);

  const showDownloadGatedPopup = useCallback(() => {
    // Minimal “popup” per request.
    window.alert(
      "Downloads require a paid subscription.\n\nPlease close this window and subscribe from the homepage.",
    );

    // If this page is opened as a popup, try to redirect the opener and close.
    try {
      if (window.opener && !window.opener.closed) {
        try {
          window.opener.location.href = "/";
        } catch {
          // Ignore cross-origin / browser restrictions.
        }
        window.close();
        return;
      }
    } catch {
      // Ignore.
    }

    redirectToFrontPage();
  }, [redirectToFrontPage]);

  const refreshUsageStatus = useCallback(async () => {
    try {
      const token = api.getAccessToken();
      const status = await api.getUsageStatus(token);
      setUsageStatus(status);
    } catch {
      // Non-fatal: usage metering is optional for UI.
    }
  }, []);

  async function doDownloadZip(token?: string | null) {
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
      const status = parseHttpStatusFromError(error);
      if (status === 429) {
        setDownloadStatus(rateLimitHint(error));
      } else if (message.includes("HTTP 401") || message.includes("HTTP 402")) {
        setDownloadStatus("Subscription required to download.");
        showDownloadGatedPopup();
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

        const desired = projectId && list.projects.some((p) => p.id === projectId)
          ? projectId
          : (list.projects[0]?.id ?? null);

        if (!desired) {
          // Do not auto-create projects on refresh.
          clearActiveSessionProjectId();
          setProjectId(null);
          setPreviewUrl(null);
          setFiles([]);
          setChatMessages([DEFAULT_ASSISTANT_MESSAGE]);
          return;
        }

        setProjectId(desired);
        setActiveSessionProjectId(desired);
        setPreviewUrl(api.previewUrl(desired));
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

  // Refresh usage status periodically.
  useEffect(() => {
    if (!document.hidden) {
      void refreshUsageStatus();
    }

    const onVisibility = () => {
      if (!document.hidden) {
        void refreshUsageStatus();
      }
    };
    document.addEventListener("visibilitychange", onVisibility);

    const id = window.setInterval(() => {
      if (document.hidden) return;
      void refreshUsageStatus();
    }, 60_000);

    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      window.clearInterval(id);
    };
  }, [refreshUsageStatus]);

  // Keep preview URL aligned when project changes.
  useEffect(() => {
    if (!projectId) return;
    setPreviewUrl(api.previewUrl(projectId));
  }, [projectId]);

  // Determine whether the preview is actually built for this project.
  useEffect(() => {
    if (!projectId) {
      setHasPreview(null);
      return;
    }
    let cancelled = false;
    setHasPreview(null);

    (async () => {
      const url = api.previewUrl(projectId);
      const ok = await checkPreviewAvailable(url);
      if (!cancelled) setHasPreview(ok);
    })();

    return () => {
      cancelled = true;
    };
  }, [projectId, checkPreviewAvailable]);

  // Load persisted chat history when project changes.
  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;

    (async () => {
      try {
        const resp = await api.getProjectChatHistory(projectId);
        if (cancelled) return;
        const msgs = resp.messages.map((m) => ({ role: m.role, content: m.content })) as api.ChatMessage[];
        setChatMessages(msgs.length ? msgs : [DEFAULT_ASSISTANT_MESSAGE]);
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
    setHasPreview(null);
    setGenerationStatus("Planning blueprint…");
    clearRevealTimers();

    try {
      const planResponse = await api.plan(goal.trim());
      const offline = coerceOfflineMeta((planResponse as any)?.meta);
      setAiOffline(offline && offline.offline ? offline : null);
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
      revealFiles(filesResponse.files, "Generating files…");

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
      setGenerationStatus(null);
      void refreshUsageStatus();
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      const status = parseHttpStatusFromError(error);
      if (status === 429) {
        setBlueprintMeta(rateLimitHint(error));
      } else if (status === 402 || message.includes("HTTP 402")) {
        setBlueprintMeta(
          "Trial AI credits exhausted. Please wait for the next month or subscribe from the homepage to continue.",
        );
      } else {
        setBlueprintMeta(`Error: ${message}`);
      }
      void refreshUsageStatus();
      setGenerationStatus(null);
    } finally {
      setIsBusy(false);
    }
  }

  function handleSelectProject(id: string, options?: { openPreview?: boolean }) {
    const shouldOpenPreview = options?.openPreview ?? true;
    setProjectId(id);
    setActiveSessionProjectId(id);
    setFiles([]);
    setBlueprintMeta(null);
    setStreamUrl(null);
    setAiOffline(null);
    setHasPreview(null);
    setShowCodePanel(true);
    const nextPreviewUrl = api.previewUrl(id);
    setPreviewUrl(nextPreviewUrl);
    setDownloadStatus(null);
    if (shouldOpenPreview) {
      window.open(nextPreviewUrl, "_blank", "noopener,noreferrer");
    }
  }

  async function handleDeleteProject(id: string) {
    if (deletingProjectId) return;
    const confirmed = window.confirm(
      "Delete this project? This removes its chat history, preview, and generated files.",
    );
    if (!confirmed) return;

    setDeletingProjectId(id);
    try {
      await api.deleteProject(id);
      const remaining = projects.filter((project) => project.id !== id);
      setProjects(remaining);

      if (projectId === id) {
        if (remaining.length > 0) {
          handleSelectProject(remaining[0].id, { openPreview: false });
        } else {
          clearActiveSessionProjectId();
          setProjectId(null);
          setFiles([]);
          setBlueprintMeta(null);
          setStreamUrl(null);
          setPreviewUrl(null);
          setDownloadStatus(null);
          setChatMessages([DEFAULT_ASSISTANT_MESSAGE]);
        }
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setBlueprintMeta(`Delete failed: ${message}`);
    } finally {
      setDeletingProjectId(null);
    }
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
      setDownloadStatus("Subscription required to download.");
      showDownloadGatedPopup();
      return;
    }
    await doDownloadZip(token);
  }

  function handlePreviewClick() {
    if (!previewUrl) return;
    if (hasPreview !== true) {
      setBlueprintMeta("No preview yet. Click Generate to build it.");
      return;
    }
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
      const offline = coerceOfflineMeta((resp as any)?.meta);
      setAiOffline(offline && offline.offline ? offline : null);
      setChatMessages((prev) => [...prev, { role: "assistant", content: resp.reply }]);
      void refreshUsageStatus();
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      const status = parseHttpStatusFromError(error);
      if (status === 429) {
        setChatMessages((prev) => [...prev, { role: "assistant", content: rateLimitHint(error) }]);
      } else if (status === 402) {
        setChatMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content:
              "Trial AI credits exhausted. Please wait for the next month or subscribe from the homepage to continue.",
          },
        ]);
      } else {
        setChatMessages((prev) => [...prev, { role: "assistant", content: `Error: ${message}` }]);
      }
    } finally {
      setIsBusy(false);
    }
  }

  async function handleUpdate() {
    const instruction = goal.trim();
    if (!instruction || !projectId) return;

    setIsBusy(true);
    setStreamUrl(null);
    setHasPreview(null);
    setBlueprintMeta("Updating app…");
    setGenerationStatus("Updating files…");
    clearRevealTimers();

    try {
      const resp = await api.patchProject(projectId, instruction, PROJECT_NAME);
      const offline = coerceOfflineMeta((resp as any)?.meta);
      setAiOffline(offline && offline.offline ? offline : null);
      const changedCount = Array.isArray(resp.changed_paths) ? resp.changed_paths.length : 0;
      const removedCount = Array.isArray(resp.removed_paths) ? resp.removed_paths.length : 0;
      setBlueprintMeta(`Updated (${changedCount} changed, ${removedCount} removed). Building preview…`);

      // Reload persisted files after patch so the file viewer stays in sync.
      try {
        const nextFiles = await api.getProjectFiles(projectId);
        if (Array.isArray(nextFiles.files)) {
          revealFiles(nextFiles.files, "Updating files…");
        }
      } catch {
        // Non-fatal: patch/build can still proceed.
      }

      const url = api.buildStreamUrl(projectId, false);
      setStreamUrl(url);
      setGenerationStatus(null);
      void refreshUsageStatus();
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      const status = parseHttpStatusFromError(error);
      if (status === 429) {
        setBlueprintMeta(rateLimitHint(error));
      } else if (status === 402 || message.includes("HTTP 402")) {
        setBlueprintMeta(
          "Trial AI credits exhausted. Please wait for the next month or subscribe from the homepage to continue.",
        );
      } else {
        setBlueprintMeta(`Update error: ${message}`);
      }
      void refreshUsageStatus();
      setGenerationStatus(null);
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
    setHasPreview(true);
  }, [projectId]);

  // Consume the build stream in the background so we can keep a clean 2-pane UI.
  useEffect(() => {
    if (!streamUrl) return;

    const source = new EventSource(streamUrl);

    // Simple progress: ticks up while streaming, hits 100% on done.
    setBuildProgress(0);
    const tick = window.setInterval(() => {
      setBuildProgress((prev) => {
        const current = typeof prev === "number" ? prev : 0;
        if (current >= 95) return current;
        // Slow ramp to avoid jumping too quickly.
        const next = current < 30 ? current + 2 : current < 70 ? current + 1 : current + 0.5;
        return Math.min(95, Math.round(next));
      });
    }, 350);

    source.addEventListener("status", (event) => {
      const data = (event as MessageEvent).data;
      if (typeof data === "string" && data && data !== "ping") {
        setBlueprintMeta(String(data));

        const lower = data.toLowerCase();
        // Best-effort nudges based on common log text.
        if (lower.includes("install")) setBuildProgress((p) => (p == null ? 15 : Math.max(p, 15)));
        if (lower.includes("build")) setBuildProgress((p) => (p == null ? 45 : Math.max(p, 45)));
        if (lower.includes("bundle") || lower.includes("vite")) setBuildProgress((p) => (p == null ? 70 : Math.max(p, 70)));
      }
    });

    source.addEventListener("done", (event) => {
      const data = (event as MessageEvent).data;
      handleBuildDone(typeof data === "string" ? data : undefined);
      setBlueprintMeta("Preview ready");
      setBuildProgress(100);
      source.close();
      window.clearInterval(tick);
      // Keep 100% visible briefly.
      window.setTimeout(() => {
        setStreamUrl(null);
        setBuildProgress(null);
      }, 600);
    });

    source.addEventListener("error", (event) => {
      const message = (event as MessageEvent).data || "Build stream error";
      setBlueprintMeta(`Error: ${String(message)}`);
      source.close();
      window.clearInterval(tick);
      setBuildProgress(null);
      setStreamUrl(null);
    });

    return () => {
      window.clearInterval(tick);
      source.close();
      setBuildProgress(null);
    };
  }, [streamUrl, handleBuildDone]);

  const subtitleText =
    blueprintMeta ??
    generationStatus ??
    (!projectId
      ? "No project yet. Click + New chat to start."
      : isBusy
        ? "Builder is thinking…"
        : typeof buildProgress === "number" && streamUrl
          ? `Building preview… ${buildProgress}%`
        : hasPreview === false
          ? "No preview yet. Click Generate to build it."
          : files.length === 0
            ? "No files yet. Describe what you want to build."
            : "Describe what you want to build.");
  const hintText =
    downloadStatus ??
    (!projectId
      ? "No project yet. Click + New chat to start."
      : hasPreview === false
        ? "No preview yet. Click Generate to create your first build."
        : "Shift+Enter for a new line. Generate to refresh the preview.");
  const disableSend = !draft.trim() || !projectId || isBusy;
  const disableGenerate = !projectId || !goal.trim() || isBusy;
  const disableUpdate = !projectId || !goal.trim() || isBusy;
  const disableDownload = !projectId || isBusy;
  const disablePreview = !previewUrl || hasPreview !== true;

  const codePanelTitle = files.length > 0 ? `Generated code (${files.length} files)` : "Generated code";

  const usageText = useMemo(() => {
    if (!usageStatus) return null;

    const t = String(usageStatus.plan_tier || "").toLowerCase();
    const planLabel =
      t === "trial" ? "Trial" :
      t === "trial_expired" ? "Trial ended" :
      t === "student" ? "Student" :
      t === "pro" ? "Pro" :
      t === "enterprise" ? "Enterprise" :
      (usageStatus.plan_tier || "Plan");

    const used = Number(usageStatus.credits_used ?? 0);
    const limit = Number(usageStatus.credits_limit ?? 0);
    if (limit > 0) return `Plan: ${planLabel} · AI Credits: ${used}/${limit}`;
    return `Plan: ${planLabel} · AI Credits: ${used}`;
  }, [usageStatus]);

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
                <div className="threadTitle">{threadQuery.trim() ? "No matches" : "No projects yet"}</div>
                <div className="threadMeta">{threadQuery.trim() ? "Adjust your search." : "Click + New chat to start."}</div>
              </div>
            ) : (
              filteredProjects.map((project) => (
                <div
                  key={project.id}
                  className={`thread ${project.id === projectId ? "active" : ""}`}
                  role="button"
                  tabIndex={0}
                  onClick={() => handleSelectProject(project.id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      handleSelectProject(project.id);
                    }
                  }}
                >
                  <div className="threadHeader">
                    <div className="threadText">
                      <div className="threadTitle">{project.name || "Untitled project"}</div>
                      <div className="threadMeta">{formatProjectTimestamp(project.updated_at)}</div>
                    </div>
                    <button
                      type="button"
                      className="threadDeleteBtn"
                      aria-label="Delete project"
                      onClick={(event) => {
                        event.stopPropagation();
                        void handleDeleteProject(project.id);
                      }}
                      disabled={deletingProjectId === project.id}
                    >
                      ×
                    </button>
                  </div>
                </div>
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
              {usageText ? <div className="usagePill">{usageText}</div> : null}
              {typeof buildProgress === "number" && streamUrl ? (
                <div className="usagePill" aria-label="Build progress">
                  Build: {buildProgress}%
                </div>
              ) : null}
              {aiOffline?.offline ? (
                <div className="usagePill" title={aiOffline.reason || "AI is temporarily unavailable"}>
                  AI: offline fallback
                </div>
              ) : null}
              <button className="ghostBtn" onClick={handlePreviewClick} disabled={disablePreview}>
                Open preview
              </button>
              <button className="ghostBtn" onClick={() => void handleDownloadClick()} disabled={disableDownload}>
                Download
              </button>
              <button className="ghostBtn" onClick={() => void handleUpdate()} disabled={disableUpdate}>
                Update
              </button>
              <button className="ghostBtn" onClick={() => void handleGenerate()} disabled={disableGenerate}>
                {isBusy ? "Working…" : "Generate"}
              </button>
            </div>
          </header>

          <section className="chatArea">
            <div style={{ display: "flex", gap: 16, height: "100%", flexWrap: "wrap" }}>
              <div style={{ flex: "2 1 520px", minWidth: 280, display: "flex", flexDirection: "column" }}>
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
              </div>

              {showCodePanel ? (
                <div
                  style={{
                    flex: "1 1 420px",
                    minWidth: 280,
                    border: "1px solid var(--border)",
                    borderRadius: 18,
                    background: "rgba(255, 255, 255, 0.03)",
                    overflow: "hidden",
                    display: "flex",
                    flexDirection: "column",
                    minHeight: 240,
                  }}
                >
                  <div
                    style={{
                      padding: "12px 14px",
                      borderBottom: "1px solid var(--border)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: 12,
                    }}
                  >
                    <div style={{ fontWeight: 600 }}>{codePanelTitle}</div>
                    <button
                      type="button"
                      className="ghostBtn"
                      onClick={() => setShowCodePanel(false)}
                      style={{ padding: "6px 10px", fontSize: 12 }}
                    >
                      Hide
                    </button>
                  </div>

                  <div style={{ padding: 12, display: "flex", flexDirection: "column", gap: 10, minHeight: 0 }}>
                    {files.length > 0 ? (
                      <select
                        value={selectedPath || files[0]?.path || ""}
                        onChange={(e) => setSelectedPath(e.target.value)}
                        style={{
                          width: "100%",
                          borderRadius: 12,
                          border: "1px solid var(--border)",
                          background: "rgba(255, 255, 255, 0.04)",
                          padding: "10px 12px",
                          fontSize: 13,
                        }}
                      >
                        {files.map((f) => (
                          <option key={f.path} value={f.path}>
                            {f.path}
                          </option>
                        ))}
                      </select>
                    ) : null}

                    {files.length === 0 ? (
                      <div style={{ color: "var(--muted)", fontSize: 13, lineHeight: 1.4 }}>
                        {generationStatus
                          ? "Generating files…"
                          : isBusy
                            ? "Working…"
                            : "Click Generate to create files. The code will appear here."}
                      </div>
                    ) : (
                      <pre
                        style={{
                          margin: 0,
                          padding: 12,
                          borderRadius: 14,
                          border: "1px solid rgba(255, 255, 255, 0.10)",
                          background: "rgba(0, 0, 0, 0.25)",
                          color: "var(--text)",
                          fontSize: 12,
                          lineHeight: 1.5,
                          overflow: "auto",
                          minHeight: 0,
                          flex: 1,
                          whiteSpace: "pre",
                        }}
                      >
                        {(selectedFile?.content ?? files[0]?.content ?? "") || ""}
                      </pre>
                    )}
                  </div>
                </div>
              ) : (
                <div style={{ flex: "1 1 200px", minWidth: 200, alignSelf: "flex-start" }}>
                  <button className="ghostBtn" type="button" onClick={() => setShowCodePanel(true)}>
                    Show code
                  </button>
                </div>
              )}
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

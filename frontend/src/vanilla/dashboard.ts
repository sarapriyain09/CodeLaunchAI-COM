import "../index.css";
import "./dashboard.css";

import * as api from "../api/orchestrator";

type StatusKind = "" | "ok" | "err";

function setStatus(el: HTMLElement, text: string, kind: StatusKind = "") {
  el.textContent = text;
  el.className = "dash-status" + (kind ? ` ${kind}` : "");
}

function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) return;
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/app/sw.js", { scope: "/app/" }).catch(() => {
      // Non-fatal.
    });
  });
}

function escapeForPre(text: string) {
  return text.replace(/[&<>]/g, (ch) => (ch === "&" ? "&amp;" : ch === "<" ? "&lt;" : "&gt;"));
}

function addBubble(chatLog: HTMLElement, role: "user" | "assistant" | "system", content: string) {
  const row = document.createElement("div");
  row.className = `msg ${role}`;

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = `
    <div class="meta">${escapeForPre(role === "user" ? "You" : role === "assistant" ? "Codlearn" : "System")}</div>
    <pre>${escapeForPre(content)}</pre>
  `;

  row.appendChild(bubble);
  chatLog.appendChild(row);
  row.scrollIntoView({ block: "end" });
}

function formatProjectLabel(p: api.Project) {
  const name = (p.name || "Project").trim() || "Project";
  const date = p.updated_at ? new Date(p.updated_at) : null;
  const suffix =
    date && !Number.isNaN(date.getTime())
      ? ` · ${date.toLocaleDateString(undefined, { month: "short", day: "numeric" })}`
      : "";
  return `${name}${suffix}`;
}

const els = {
  // top menu
  userLine: document.getElementById("userLine") as HTMLDivElement,
  name: document.getElementById("name") as HTMLInputElement,
  email: document.getElementById("email") as HTMLInputElement,
  signIn: document.getElementById("signIn") as HTMLButtonElement,
  signOut: document.getElementById("signOut") as HTMLButtonElement,
  authStatus: document.getElementById("authStatus") as HTMLDivElement,

  projectSelect: document.getElementById("projectSelect") as HTMLSelectElement,
  newProject: document.getElementById("newProject") as HTMLButtonElement,
  openPreview: document.getElementById("openPreview") as HTMLAnchorElement,
  projectStatus: document.getElementById("projectStatus") as HTMLDivElement,

  // chat
  chatLog: document.getElementById("chatLog") as HTMLDivElement,
  message: document.getElementById("message") as HTMLTextAreaElement,
  generate: document.getElementById("generate") as HTMLButtonElement,
  send: document.getElementById("send") as HTMLButtonElement,
  clearChat: document.getElementById("clearChat") as HTMLButtonElement,
  chatStatus: document.getElementById("chatStatus") as HTMLDivElement,
};

const ACTIVE_PROJECT_KEY = "cla_active_project_id";

function getActiveProjectId(): string | null {
  return localStorage.getItem(ACTIVE_PROJECT_KEY);
}

function setActiveProjectId(id: string) {
  localStorage.setItem(ACTIVE_PROJECT_KEY, id);
}

let projects: api.Project[] = [];
let activeProjectId: string | null = getActiveProjectId();
let buildSource: EventSource | null = null;

function stopBuildStream() {
  if (!buildSource) return;
  try {
    buildSource.close();
  } catch {
    // ignore
  }
  buildSource = null;
}

function syncPreviewLink() {
  if (!activeProjectId) {
    els.openPreview.href = "#";
    els.openPreview.setAttribute("aria-disabled", "true");
    return;
  }

  els.openPreview.href = api.previewUrl(activeProjectId);
  els.openPreview.removeAttribute("aria-disabled");
}

function renderProjectSelect() {
  els.projectSelect.innerHTML = "";

  for (const p of projects) {
    const opt = document.createElement("option");
    opt.value = p.id;
    opt.textContent = formatProjectLabel(p);
    els.projectSelect.appendChild(opt);
  }

  if (activeProjectId && projects.some((p) => p.id === activeProjectId)) {
    els.projectSelect.value = activeProjectId;
  } else {
    activeProjectId = projects[0]?.id ?? null;
    if (activeProjectId) setActiveProjectId(activeProjectId);
    if (activeProjectId) els.projectSelect.value = activeProjectId;
  }

  syncPreviewLink();
}

async function refreshProjects() {
  setStatus(els.projectStatus, "Loading projects…");

  try {
    const list = await api.listProjects();
    projects = list.projects ?? [];

    if (!projects.length) {
      const created = await api.createProject();
      projects = [created];
      activeProjectId = created.id;
      setActiveProjectId(created.id);
    }

    renderProjectSelect();
    setStatus(els.projectStatus, `Loaded ${projects.length} project(s).`, "ok");
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    setStatus(els.projectStatus, `Failed to load projects: ${msg}`, "err");
  }
}

async function signIn() {
  const email = els.email.value.trim();
  const name = els.name.value.trim() || null;

  if (!email) {
    setStatus(els.authStatus, "Email is required.", "err");
    return;
  }

  els.signIn.disabled = true;
  setStatus(els.authStatus, "Signing in…");

  try {
    const resp = await api.authGuest({ email, name });
    api.setAccessToken(resp.access_token);
    setStatus(els.authStatus, "Signed in.", "ok");
    els.userLine.textContent = resp.user.email;
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    setStatus(els.authStatus, `Sign in failed: ${msg}`, "err");
  } finally {
    els.signIn.disabled = false;
  }
}

async function hydrateUser() {
  const token = api.getAccessToken();
  if (!token) {
    els.userLine.textContent = "Not signed in";
    return;
  }

  setStatus(els.authStatus, "Checking session…");

  try {
    const me = await api.me(token);
    els.userLine.textContent = me.email;
    setStatus(els.authStatus, "Signed in.", "ok");
  } catch {
    api.clearAccessToken();
    els.userLine.textContent = "Not signed in";
    setStatus(els.authStatus, "Session expired. Please sign in again.", "err");
  }
}

function signOut() {
  api.clearAccessToken();
  els.userLine.textContent = "Not signed in";
  setStatus(els.authStatus, "Signed out.", "ok");
}

async function newProject() {
  els.newProject.disabled = true;
  setStatus(els.projectStatus, "Creating project…");

  try {
    const created = await api.createProject();
    projects = [created, ...projects];
    activeProjectId = created.id;
    setActiveProjectId(created.id);
    renderProjectSelect();
    setStatus(els.projectStatus, "Project created.", "ok");

    els.chatLog.innerHTML = "";
    addBubble(els.chatLog, "assistant", "New project created. Describe what you want to build.");
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    setStatus(els.projectStatus, `Failed to create project: ${msg}`, "err");
  } finally {
    els.newProject.disabled = false;
  }
}

async function ensureProject(): Promise<string | null> {
  if (activeProjectId) return activeProjectId;

  setStatus(els.projectStatus, "Creating project…");

  try {
    const created = await api.createProject();
    projects = [created, ...projects];
    activeProjectId = created.id;
    setActiveProjectId(created.id);
    renderProjectSelect();
    setStatus(els.projectStatus, "Project created.", "ok");
    return created.id;
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    setStatus(els.projectStatus, `Failed to create project: ${msg}`, "err");
    return null;
  }
}

async function generatePreview() {
  const goal = els.message.value.trim();
  if (!goal) {
    setStatus(els.chatStatus, "Type what you want to build, then click Generate.", "err");
    return;
  }

  const projectId = await ensureProject();
  if (!projectId) return;

  els.generate.disabled = true;
  els.send.disabled = true;
  setStatus(els.chatStatus, "Planning blueprint…");
  addBubble(els.chatLog, "user", goal);

  try {
    const plan = await api.plan(goal);
    setStatus(els.chatStatus, "Generating project files…");
    await api.materialize(projectId, plan.blueprint, "generated-app");

    // Stream the build so users see progress.
    stopBuildStream();
    const url = api.buildStreamUrl(projectId, true);
    buildSource = new EventSource(url);

    buildSource.addEventListener("status", (event) => {
      const data = (event as MessageEvent).data;
      if (typeof data === "string" && data && data !== "ping") {
        setStatus(els.chatStatus, data);
      }
    });

    buildSource.addEventListener("log", (event) => {
      const data = (event as MessageEvent).data;
      if (typeof data === "string" && data.trim()) {
        const lower = data.toLowerCase();
        if (lower.includes("install") || lower.includes("build") || lower.includes("vite")) {
          setStatus(els.chatStatus, data);
        }
      }
    });

    buildSource.addEventListener("done", () => {
      stopBuildStream();
      const preview = api.previewUrl(projectId) + `?t=${Date.now()}`;
      syncPreviewLink();
      setStatus(els.chatStatus, "Preview ready.", "ok");
      window.open(preview, "_blank", "noopener,noreferrer");
      els.generate.disabled = false;
      els.send.disabled = false;
    });

    buildSource.addEventListener("error", (event) => {
      const data = (event as MessageEvent).data;
      stopBuildStream();
      setStatus(els.chatStatus, `Build error: ${String(data || "unknown")}`, "err");
      els.generate.disabled = false;
      els.send.disabled = false;
    });

    // Note: buttons are re-enabled when stream ends (done/error).
    return;
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    addBubble(els.chatLog, "assistant", `Error: ${msg}`);
    setStatus(els.chatStatus, "Generate failed.", "err");
  } finally {
    if (!buildSource) {
      els.generate.disabled = false;
      els.send.disabled = false;
    }
  }
}

async function sendMessage() {
  const text = els.message.value.trim();
  if (!text) return;

  if (!activeProjectId) {
    setStatus(els.chatStatus, "No active project. Try creating one.", "err");
    return;
  }

  els.send.disabled = true;
  setStatus(els.chatStatus, "Sending…");

  try {
    addBubble(els.chatLog, "user", text);
    els.message.value = "";

    const resp = await api.projectChat(activeProjectId, text);
    addBubble(els.chatLog, "assistant", resp.reply);
    setStatus(els.chatStatus, "Done.", "ok");
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    setStatus(els.chatStatus, `Chat failed: ${msg}`, "err");
  } finally {
    els.send.disabled = false;
  }
}

function clearChat() {
  els.chatLog.innerHTML = "";
  setStatus(els.chatStatus, "Cleared.", "ok");
}

function wireEvents() {
  els.signIn.addEventListener("click", () => void signIn());
  els.signOut.addEventListener("click", () => signOut());
  els.newProject.addEventListener("click", () => void newProject());

  els.projectSelect.addEventListener("change", () => {
    activeProjectId = els.projectSelect.value || null;
    if (activeProjectId) setActiveProjectId(activeProjectId);
    syncPreviewLink();
    setStatus(els.projectStatus, "Active project updated.", "ok");
  });

  els.send.addEventListener("click", () => void sendMessage());
  els.generate.addEventListener("click", () => void generatePreview());
  els.clearChat.addEventListener("click", () => clearChat());

  els.message.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      void sendMessage();
    }
  });
}

async function main() {
  registerServiceWorker();
  wireEvents();

  addBubble(
    els.chatLog,
    "assistant",
    "Tell me what you want to build. I’ll ask a couple of clarifying questions, then you can subscribe if you want downloads.",
  );

  await hydrateUser();
  await refreshProjects();
}

void main();

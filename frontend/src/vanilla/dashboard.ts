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
    const base = (import.meta as any).env?.BASE_URL || "/";
    const scope = typeof base === "string" ? (base.endsWith("/") ? base : `${base}/`) : "/";
    navigator.serviceWorker.register(`${scope}sw.js`, { scope }).catch(() => {
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

  updateEmptyState();
}

function updateEmptyState() {
  const chatCenter = document.querySelector(".chatCenter") as HTMLElement | null;
  if (!chatCenter) return;
  const isEmpty = els.chatLog.childElementCount === 0;
  chatCenter.classList.toggle("empty", isEmpty);
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
  signIn: document.getElementById("signIn") as HTMLButtonElement,
  signOut: document.getElementById("signOut") as HTMLButtonElement,
  getStarted: document.getElementById("getStarted") as HTMLButtonElement | null,
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
const SPEC_KEY_PREFIX = "cla_site_spec_";
const AWAITING_SPEC_KEY_PREFIX = "cla_site_spec_awaiting_";
const PREVIEW_READY_KEY_PREFIX = "cla_preview_ready_";

function setAuthButtons(signedIn: boolean) {
  els.signIn.hidden = signedIn;
  els.signOut.hidden = !signedIn;
}

function getActiveProjectId(): string | null {
  return localStorage.getItem(ACTIVE_PROJECT_KEY);
}

function setActiveProjectId(id: string) {
  localStorage.setItem(ACTIVE_PROJECT_KEY, id);
}

function specKey(projectId: string) {
  return `${SPEC_KEY_PREFIX}${projectId}`;
}

function awaitingSpecKey(projectId: string) {
  return `${AWAITING_SPEC_KEY_PREFIX}${projectId}`;
}

function getProjectSpec(projectId: string): string | null {
  const raw = localStorage.getItem(specKey(projectId));
  return raw && raw.trim() ? raw : null;
}

function setProjectSpec(projectId: string, spec: string) {
  localStorage.setItem(specKey(projectId), spec.trim());
  localStorage.removeItem(awaitingSpecKey(projectId));
  syncGenerateButton();
}

function isAwaitingSpec(projectId: string): boolean {
  return localStorage.getItem(awaitingSpecKey(projectId)) === "1";
}

function setAwaitingSpec(projectId: string, awaiting: boolean) {
  if (awaiting) localStorage.setItem(awaitingSpecKey(projectId), "1");
  else localStorage.removeItem(awaitingSpecKey(projectId));
  syncGenerateButton();
}

function syncGenerateButton() {
  if (!activeProjectId) {
    els.generate.hidden = true;
    return;
  }

  const hasSpec = Boolean(getProjectSpec(activeProjectId));
  const awaiting = isAwaitingSpec(activeProjectId);

  // UX: hide Generate until we've asked for (and are awaiting) a clarifying spec.
  // Once a spec is saved, keep Generate available.
  els.generate.hidden = !(hasSpec || awaiting);
}

function previewReadyKey(projectId: string) {
  return `${PREVIEW_READY_KEY_PREFIX}${projectId}`;
}

function isPreviewReady(projectId: string): boolean {
  return localStorage.getItem(previewReadyKey(projectId)) === "1";
}

function markPreviewReady(projectId: string) {
  localStorage.setItem(previewReadyKey(projectId), "1");
}

function specQuestions(): string {
  return [
    "Before I generate, answer these (copy/paste with answers):",
    "1) Website type (landing page, portfolio, SaaS, ecommerce, etc.)?",
    "2) Business/name + one-line tagline?",
    "3) Target audience?",
    "4) Pages needed (Home, Pricing, About, Contact, etc.)?",
    "5) Must-have sections/features (CTA, newsletter, testimonials, gallery, FAQ, forms)?",
    "6) Visual style (minimal, bold, playful) + preferred colors?",
    "7) Primary call-to-action (Book demo, Subscribe, Buy, Contact)?",
    "",
    "After answering, click Generate.",
  ].join("\n");
}

function ensureSpecOrAsk(projectId: string, source: "chat" | "generate"): boolean {
  const spec = getProjectSpec(projectId);
  if (spec) return true;

  if (!isAwaitingSpec(projectId)) {
    setAwaitingSpec(projectId, true);
    addBubble(
      els.chatLog,
      "assistant",
      source === "generate"
        ? specQuestions()
        : ["I can generate a full website, but I need a quick spec first.", "", specQuestions()].join("\n"),
    );
  }

  setStatus(els.chatStatus, "Waiting for website spec (answer the questions).", "ok");
  return false;
}

let projects: api.Project[] = [];
let activeProjectId: string | null = getActiveProjectId();
let buildSource: EventSource | null = null;
let usageStatus: api.UsageStatus | null = null;


function isSubscribedUser(): boolean {
  return Boolean(usageStatus?.subscribed);
}

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
  if (!activeProjectId || !isPreviewReady(activeProjectId)) {
    els.openPreview.href = "#";
    els.openPreview.setAttribute("aria-disabled", "true");
    els.openPreview.hidden = true;
    return;
  }

  els.openPreview.href = api.previewUrl(activeProjectId);
  els.openPreview.removeAttribute("aria-disabled");
  els.openPreview.hidden = false;
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
  syncGenerateButton();
}

async function refreshProjects() {
  // Keep the top bar clean for trial/single-project users.
  // Only show project status when something goes wrong.
  setStatus(els.projectStatus, "");

  try {
    const list = await api.listProjects();
    projects = list.projects ?? [];

    // Trial users should always have exactly 1 project created for them.
    // Subscribed users can create as many as they want.
    if (!isSubscribedUser() && projects.length === 0) {
      const created = await api.createProject();
      projects = [created];
      activeProjectId = created.id;
      setActiveProjectId(created.id);
    }

    renderProjectSelect();
    setStatus(els.projectStatus, "");
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    setStatus(els.projectStatus, `Failed to load projects: ${msg}`, "err");
  }
}

async function signIn() {
  const emailRaw = window.prompt("Email:") ?? "";
  const email = emailRaw.trim();
  if (!email) return;
  const nameRaw = window.prompt("Name (optional):") ?? "";
  const name = nameRaw.trim() || null;

  els.signIn.disabled = true;
  setStatus(els.authStatus, "Signing in…");

  try {
    const resp = await api.authGuest({ email, name });
    api.setAccessToken(resp.access_token);
    setStatus(els.authStatus, "Signed in.", "ok");
    els.userLine.textContent = resp.user.email;
    setAuthButtons(true);

    await hydrateUsage();
    await refreshProjects();
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    setStatus(els.authStatus, `Sign in failed: ${msg}`, "err");
    setAuthButtons(false);
  } finally {
    els.signIn.disabled = false;
  }
}

async function hydrateUser() {
  const token = api.getAccessToken();
  if (!token) {
    els.userLine.textContent = "";
    setAuthButtons(false);
    return;
  }

  setStatus(els.authStatus, "Checking session…");

  try {
    const me = await api.me(token);
    els.userLine.textContent = me.email;
    setStatus(els.authStatus, "Signed in.", "ok");
    setAuthButtons(true);
  } catch {
    api.clearAccessToken();
    els.userLine.textContent = "";
    setStatus(els.authStatus, "Session expired. Please sign in again.", "err");
    setAuthButtons(false);
  }
}

function signOut() {
  api.clearAccessToken();
  els.userLine.textContent = "";
  setStatus(els.authStatus, "Signed out.", "ok");
  setAuthButtons(false);

  usageStatus = null;
  void hydrateUsage().then(() => refreshProjects());
}

async function newProject() {
  if (!isSubscribedUser() && projects.length >= 1) {
    setStatus(els.projectStatus, "Trial users can have 1 project. Subscribe for unlimited projects.", "err");
    return;
  }

  els.newProject.disabled = true;
  setStatus(els.projectStatus, "");

  try {
    const created = await api.createProject();
    projects = [created, ...projects];
    activeProjectId = created.id;
    setActiveProjectId(created.id);
    renderProjectSelect();
    setStatus(els.projectStatus, "");

    els.chatLog.innerHTML = "";
    addBubble(els.chatLog, "assistant", "New project created. Describe what you want to build.");
    syncGenerateButton();
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    setStatus(els.projectStatus, `Failed to create project: ${msg}`, "err");
  } finally {
    els.newProject.disabled = false;
  }
}

async function ensureProject(): Promise<string | null> {
  if (activeProjectId) return activeProjectId;

  // If we already have projects loaded, prefer selecting an existing project
  // over creating a new one (especially for trial users).
  if (projects.length > 0) {
    activeProjectId = projects[0].id;
    setActiveProjectId(activeProjectId);
    renderProjectSelect();
    return activeProjectId;
  }

  if (!isSubscribedUser() && projects.length >= 1) {
    setStatus(els.projectStatus, "Trial users can have 1 project. Subscribe for unlimited projects.", "err");
    return null;
  }

  setStatus(els.projectStatus, "");

  try {
    const created = await api.createProject();
    projects = [created, ...projects];
    activeProjectId = created.id;
    setActiveProjectId(created.id);
    renderProjectSelect();
    setStatus(els.projectStatus, "");
    return created.id;
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    setStatus(els.projectStatus, `Failed to create project: ${msg}`, "err");
    return null;
  }
}

async function generatePreview() {
  const goal = els.message.value.trim();
  const projectId = await ensureProject();
  if (!projectId) return;

  activeProjectId = projectId;
  syncPreviewLink();

  if (!ensureSpecOrAsk(projectId, "generate")) return;

  const spec = getProjectSpec(projectId);
  const effectiveGoal = goal || (spec ?? "");
  if (!effectiveGoal) {
    setStatus(els.chatStatus, "Type what you want to build, then click Generate.", "err");
    return;
  }

  els.generate.disabled = true;
  els.send.disabled = true;
  setStatus(els.chatStatus, "Planning blueprint…");
  addBubble(els.chatLog, "user", effectiveGoal);

  try {
    const plan = await api.plan(effectiveGoal, spec ? { website_spec: spec } : undefined);
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
      markPreviewReady(projectId);
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

  const projectId = await ensureProject();
  if (!projectId) return;
  activeProjectId = projectId;
  syncPreviewLink();

  // If we're collecting a website spec, treat this message as the answers.
  if (isAwaitingSpec(projectId)) {
    addBubble(els.chatLog, "user", text);
    els.message.value = "";
    setProjectSpec(projectId, text);
    addBubble(
      els.chatLog,
      "assistant",
      "Got it. Now click Generate to build the first version. You can also Send follow-ups to iterate.",
    );
    setStatus(els.chatStatus, "Spec saved.", "ok");
    return;
  }

  if (!ensureSpecOrAsk(projectId, "chat")) {
    addBubble(els.chatLog, "user", text);
    els.message.value = "";
    syncGenerateButton();
    return;
  }

  els.send.disabled = true;
  setStatus(els.chatStatus, "Sending…");

  try {
    addBubble(els.chatLog, "user", text);
    els.message.value = "";

    const spec = getProjectSpec(projectId);
    const resp = await api.projectChat(projectId, text, spec ? { website_spec: spec } : undefined);
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
  updateEmptyState();
}

function wireEvents() {
  els.signIn.addEventListener("click", () => void signIn());
  els.signOut.addEventListener("click", () => signOut());
  els.newProject.addEventListener("click", () => void newProject());

  els.getStarted?.addEventListener("click", () => {
    els.message.focus();
  });

  els.projectSelect.addEventListener("change", () => {
    activeProjectId = els.projectSelect.value || null;
    if (activeProjectId) setActiveProjectId(activeProjectId);
    syncPreviewLink();
    syncGenerateButton();
    setStatus(els.projectStatus, "");
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

async function hydrateUsage() {
  try {
    const token = api.getAccessToken();
    usageStatus = await api.getUsageStatus(token);
  } catch {
    // Non-fatal; treat unknown as trial.
    usageStatus = {
      period: "",
      plan_tier: "trial",
      credits_used: 0,
      credits_limit: 0,
      credits_remaining: 0,
      tokens_used: 0,
      subscribed: false,
    };
  }
}

async function main() {
  registerServiceWorker();
  wireEvents();

  setAuthButtons(false);

  updateEmptyState();

  // Default: hidden until clarifying questions are asked.
  syncGenerateButton();

  await hydrateUser();
  await hydrateUsage();
  await refreshProjects();
}

void main();

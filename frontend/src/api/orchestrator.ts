export type Blueprint = Record<string, unknown>;

export type FileItem = {
  path: string;
  content: string;
};

export type ChatMessage = {
  role: "system" | "user" | "assistant";
  content: string;
};

export type ProjectChatHistoryItem = {
  role: ChatMessage["role"];
  content: string;
  created_at: string;
};

export type Project = {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
};

export type UserPublic = {
  id: string;
  email: string;
  name?: string | null;
  picture?: string | null;
};

export type AuthResponse = {
  access_token: string;
  token_type: "bearer";
  user: UserPublic;
};

export type ProjectState = {
  project_id: string;
  updated_at: string;
  blueprint: Record<string, unknown>;
  plan: Record<string, unknown>;
};

export type ProjectFiles = {
  project_id: string;
  updated_at: string;
  files: FileItem[];
};

export type PatchResponse = {
  project_id: string;
  changed_paths: string[];
  removed_paths: string[];
  file_count: number;
  meta?: unknown;
};

export type UsageStatus = {
  period: string;
  plan_tier: "trial" | "trial_expired" | "student" | "pro" | "enterprise" | string;
  credits_used: number;
  credits_limit: number;
  credits_remaining: number;
  tokens_used: number;
  subscribed: boolean;
  trial_active?: boolean;
  trial_days?: number;
  actor?: string;
};

function normalizeBaseUrl(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) return "";

  // Windows often resolves localhost -> ::1 (IPv6). If the backend is bound to 127.0.0.1,
  // calls to http://localhost:<port> can fail. Normalize to IPv4 loopback.
  return trimmed.replace("://localhost", "://127.0.0.1");
}

const ORCH_BASE =
  normalizeBaseUrl(String(import.meta.env.VITE_ORCH_BASE_URL ?? "")) ||
  (typeof window !== "undefined" ? window.location.origin : "http://127.0.0.1:7080");

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${ORCH_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(`HTTP ${response.status} ${response.statusText}: ${detail.slice(0, 500)}`);
  }

  return response.json() as Promise<T>;
}

const TOKEN_KEY = "cla_access_token";

export function getAccessToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setAccessToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearAccessToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export async function authGuest(payload: { email: string; name: string | null }) {
  return http<AuthResponse>("/auth/guest", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function me(token: string) {
  const response = await fetch(`${ORCH_BASE}/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(`HTTP ${response.status} ${response.statusText}: ${detail.slice(0, 500)}`);
  }

  return (await response.json()) as UserPublic;
}

export async function plan(goal: string, context?: Record<string, unknown>) {
  return http<{ blueprint: Blueprint; meta?: unknown }>("/plan", {
    method: "POST",
    body: JSON.stringify({ goal, context: context ?? null }),
  });
}

export async function chat(messages: ChatMessage[], context?: Record<string, unknown>) {
  return http<{ reply: string; meta?: unknown }>("/chat", {
    method: "POST",
    body: JSON.stringify({ messages, context: context ?? null }),
  });
}

export async function projectChat(projectId: string, message: string, context?: Record<string, unknown>) {
  return http<{ reply: string; meta?: unknown }>(`/projects/${encodeURIComponent(projectId)}/chat`, {
    method: "POST",
    body: JSON.stringify({ message, context: context ?? null }),
  });
}

export async function getProjectChatHistory(projectId: string) {
  return http<{ project_id: string; messages: ProjectChatHistoryItem[] }>(
    `/projects/${encodeURIComponent(projectId)}/chat/history`,
    { method: "GET" },
  );
}

export async function getProjectState(projectId: string): Promise<ProjectState> {
  return http<ProjectState>(`/projects/${encodeURIComponent(projectId)}/state`, { method: "GET" });
}

export async function putProjectState(
  projectId: string,
  body: { blueprint?: Record<string, unknown>; plan?: Record<string, unknown> },
): Promise<ProjectState> {
  return http<ProjectState>(`/projects/${encodeURIComponent(projectId)}/state`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export async function getProjectFiles(projectId: string): Promise<ProjectFiles> {
  return http<ProjectFiles>(`/projects/${encodeURIComponent(projectId)}/files`, { method: "GET" });
}

export async function putProjectFiles(projectId: string, files: FileItem[]): Promise<ProjectFiles> {
  return http<ProjectFiles>(`/projects/${encodeURIComponent(projectId)}/files`, {
    method: "PUT",
    body: JSON.stringify({ files }),
  });
}

export async function generateFiles(blueprint: Blueprint, projectName: string) {
  return http<{ files: FileItem[] }>("/generate", {
    method: "POST",
    body: JSON.stringify({ blueprint, project_name: projectName }),
  });
}

export async function materialize(
  projectId: string,
  blueprint: Blueprint,
  projectName: string,
) {
  return http<{ project_id: string; workspace_path: string; file_count: number }>(
    `/projects/${encodeURIComponent(projectId)}/materialize`,
    {
      method: "POST",
      body: JSON.stringify({ blueprint, project_name: projectName }),
    },
  );
}

export async function patchProject(projectId: string, instruction: string, projectName: string) {
  return http<PatchResponse>(`/projects/${encodeURIComponent(projectId)}/patch`, {
    method: "POST",
    body: JSON.stringify({ instruction, project_name: projectName }),
  });
}

export async function listProjects() {
  return http<{ projects: Project[] }>("/projects");
}

export async function createProject(name?: string, projectId?: string) {
  return http<Project>("/projects", {
    method: "POST",
    body: JSON.stringify({
      name: name ?? null,
      project_id: projectId ?? null,
    }),
  });
}

export async function deleteProject(projectId: string) {
  return http<{ deleted: boolean }>(`/projects/${encodeURIComponent(projectId)}`, {
    method: "DELETE",
  });
}

export async function getProject(projectId: string) {
  return http<Project>(`/projects/${encodeURIComponent(projectId)}`);
}

export function buildStreamUrl(projectId: string, install = true) {
  return `${ORCH_BASE}/projects/${encodeURIComponent(projectId)}/build/stream?install=${install ? "true" : "false"}`;
}

export function previewUrl(projectId: string) {
  return `${ORCH_BASE}/preview/${encodeURIComponent(projectId)}/`;
}

export async function exportZip(projectId: string, token?: string | null): Promise<Blob> {
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${ORCH_BASE}/projects/${encodeURIComponent(projectId)}/export.zip`, {
    headers,
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(`HTTP ${response.status} ${response.statusText}: ${detail.slice(0, 500)}`);
  }

  return response.blob();
}

export async function billingStatus(token: string): Promise<{ subscribed: boolean }> {
  const response = await fetch(`${ORCH_BASE}/billing/status`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(`HTTP ${response.status} ${response.statusText}: ${detail.slice(0, 500)}`);
  }

  return (await response.json()) as { subscribed: boolean };
}

export async function getUsageStatus(token?: string | null): Promise<UsageStatus> {
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${ORCH_BASE}/usage/status`, { headers });
  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(`HTTP ${response.status} ${response.statusText}: ${detail.slice(0, 500)}`);
  }
  return (await response.json()) as UsageStatus;
}

export type BillingInterval = "month" | "year";
export type BillingPlan = "student" | "pro";

export async function createCheckoutSession(
  token: string,
  plan: BillingPlan = "pro",
  interval: BillingInterval = "month",
): Promise<{ url: string | null; already_subscribed?: boolean }> {
  const response = await fetch(`${ORCH_BASE}/billing/checkout-session`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ plan, interval }),
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(`HTTP ${response.status} ${response.statusText}: ${detail.slice(0, 500)}`);
  }

  return (await response.json()) as { url: string | null; already_subscribed?: boolean };
}

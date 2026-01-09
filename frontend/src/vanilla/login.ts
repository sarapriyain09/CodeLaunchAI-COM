import "../index.css";
import "./dashboard.css";
import "./landing-legacy.css";
import "./login.css";

import * as api from "../api/orchestrator";

type StatusKind = "" | "ok" | "err";

function setStatus(el: HTMLElement, text: string, kind: StatusKind = "") {
  el.textContent = text;
  el.className = "dash-status" + (kind ? ` ${kind}` : "");
}

function baseUrl(): string {
  const base = (import.meta as any).env?.BASE_URL || "/";
  if (typeof base !== "string") return "/";
  return base.endsWith("/") ? base : `${base}/`;
}

function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) return;
  window.addEventListener("load", () => {
    const scope = baseUrl();
    navigator.serviceWorker.register(`${scope}sw.js`, { scope }).catch(() => {
      // Non-fatal.
    });
  });
}

function showTab(mode: "login" | "register") {
  const tabLogin = document.getElementById("tabLogin") as HTMLButtonElement;
  const tabRegister = document.getElementById("tabRegister") as HTMLButtonElement;
  const loginForm = document.getElementById("loginForm") as HTMLFormElement;
  const registerForm = document.getElementById("registerForm") as HTMLFormElement;

  const isLogin = mode === "login";
  tabLogin.setAttribute("aria-selected", isLogin ? "true" : "false");
  tabRegister.setAttribute("aria-selected", isLogin ? "false" : "true");

  loginForm.hidden = !isLogin;
  registerForm.hidden = isLogin;

  const focusId = isLogin ? "loginEmail" : "firstName";
  window.setTimeout(() => (document.getElementById(focusId) as HTMLInputElement | null)?.focus(), 0);
}

async function finishAuth(resp: api.AuthResponse) {
  api.setAccessToken(resp.access_token);
  // Send them to the app (home).
  window.location.href = baseUrl();
}

function wire() {
  const formStatus = document.getElementById("formStatus") as HTMLDivElement;

  const tabLogin = document.getElementById("tabLogin") as HTMLButtonElement;
  const tabRegister = document.getElementById("tabRegister") as HTMLButtonElement;
  const goRegister = document.getElementById("goRegister") as HTMLButtonElement;
  const goLogin = document.getElementById("goLogin") as HTMLButtonElement;

  const loginForm = document.getElementById("loginForm") as HTMLFormElement;
  const registerForm = document.getElementById("registerForm") as HTMLFormElement;

  tabLogin.addEventListener("click", () => showTab("login"));
  tabRegister.addEventListener("click", () => showTab("register"));
  goRegister.addEventListener("click", () => showTab("register"));
  goLogin.addEventListener("click", () => showTab("login"));

  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    setStatus(formStatus, "Signing in…");

    const email = (document.getElementById("loginEmail") as HTMLInputElement).value.trim();
    const password = (document.getElementById("loginPassword") as HTMLInputElement).value;

    try {
      const resp = await api.authLogin({ email, password });
      setStatus(formStatus, "Signed in.", "ok");
      await finishAuth(resp);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      const lower = msg.toLowerCase();
      const encourageRegister = lower.includes("401") || lower.includes("invalid email") || lower.includes("invalid");
      setStatus(
        formStatus,
        encourageRegister
          ? "Login failed. If you don’t have an account yet, register below."
          : `Login failed: ${msg}`,
        "err",
      );
      if (encourageRegister) showTab("register");
    }
  });

  registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    setStatus(formStatus, "Creating account…");

    const first_name = (document.getElementById("firstName") as HTMLInputElement).value.trim();
    const last_name = (document.getElementById("lastName") as HTMLInputElement).value.trim();
    const email = (document.getElementById("registerEmail") as HTMLInputElement).value.trim();
    const password = (document.getElementById("registerPassword") as HTMLInputElement).value;

    try {
      const resp = await api.authRegister({ first_name, last_name, email, password });
      setStatus(formStatus, "Account created.", "ok");
      await finishAuth(resp);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setStatus(formStatus, `Registration failed: ${msg}`, "err");
    }
  });

  // If already signed in, bounce back to app.
  const token = api.getAccessToken();
  if (token) {
    setStatus(formStatus, "You’re already signed in. Redirecting…", "ok");
    window.setTimeout(() => {
      window.location.href = baseUrl();
    }, 250);
  }
}

registerServiceWorker();
wire();

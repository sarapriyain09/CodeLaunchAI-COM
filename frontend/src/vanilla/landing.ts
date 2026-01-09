import "../index.css";
import "./dashboard.css";
import "./landing-legacy.css";

import * as api from "../api/orchestrator";

function scrollToId(id: string) {
  const element = document.getElementById(id);
  if (element) element.scrollIntoView({ behavior: "smooth" });
}

function wireNavScroll() {
  const buttons = document.querySelectorAll<HTMLButtonElement>("button[data-scroll]");
  for (const btn of buttons) {
    btn.addEventListener("click", () => {
      const target = btn.getAttribute("data-scroll");
      if (target) scrollToId(target);
    });
  }
}

function handleScrollQueryParam() {
  const params = new URLSearchParams(window.location.search);
  const target = params.get("scroll");
  if (!target) return;
  window.setTimeout(() => scrollToId(target), 0);
}

function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) return;
  window.addEventListener("load", () => {
    const base = (import.meta as any).env?.BASE_URL || "/";
    const scope = typeof base === "string" ? (base.endsWith("/") ? base : `${base}/`) : "/";
    navigator.serviceWorker.register(`${scope}sw.js`, { scope }).catch(() => {
      // Non-fatal: installability will just be disabled.
    });
  });
}

function wireAuthButtons() {
  const signIn = document.getElementById("signIn") as HTMLButtonElement | null;
  const signOut = document.getElementById("signOut") as HTMLButtonElement | null;
  if (!signIn && !signOut) return;

  const sync = () => {
    const signedIn = Boolean(api.getAccessToken());
    if (signIn) signIn.hidden = signedIn;
    if (signOut) signOut.hidden = !signedIn;
  };

  signIn?.addEventListener("click", () => {
    // Use the app page for actual sign-in flow.
    const base = (import.meta as any).env?.BASE_URL || "/";
    window.location.href = typeof base === "string" ? base : "/";
  });

  signOut?.addEventListener("click", () => {
    api.clearAccessToken();
    sync();
  });

  sync();
}

wireNavScroll();
handleScrollQueryParam();
registerServiceWorker();
wireAuthButtons();

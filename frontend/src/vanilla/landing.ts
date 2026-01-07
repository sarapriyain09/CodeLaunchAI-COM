import "../index.css";
import "../pages/landing-legacy.css";

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
    navigator.serviceWorker.register("/app/sw.js", { scope: "/app/" }).catch(() => {
      // Non-fatal: installability will just be disabled.
    });
  });
}

wireNavScroll();
handleScrollQueryParam();
registerServiceWorker();

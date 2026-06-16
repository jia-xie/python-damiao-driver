/** Light/dark theme, default light, persisted. Applied via data-theme on <html>. */

export type Theme = "light" | "dark";
const KEY = "damiao.monitor.theme";

export function getTheme(): Theme {
  const t = localStorage.getItem(KEY);
  return t === "dark" ? "dark" : "light"; // default light
}

export function applyTheme(t: Theme) {
  document.documentElement.setAttribute("data-theme", t);
}

export function setTheme(t: Theme) {
  try {
    localStorage.setItem(KEY, t);
  } catch {
    /* ignore */
  }
  applyTheme(t);
}

export function initTheme() {
  applyTheme(getTheme());
}

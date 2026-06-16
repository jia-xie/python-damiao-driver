import { useState } from "react";
import { useApp } from "../lib/store";
import { useWidgets } from "../lib/widgets";
import { PANELS } from "../panels/registry";
import { getTheme, setTheme, type Theme } from "../lib/theme";
import { api } from "../lib/control";

export default function Toolbar() {
  const connected = useApp((s) => s.connected);
  const status = useApp((s) => s.status);
  const mode = useApp((s) => s.mode);
  const setMode = useApp((s) => s.setMode);
  const setControlMotors = useApp((s) => s.setControlMotors);
  const setCurrentMotor = useApp((s) => s.setCurrentMotor);
  const addWidget = useWidgets((s) => s.addWidget);
  const resetWidgets = useWidgets((s) => s.resetWidgets);
  const [theme, setThemeState] = useState<Theme>(getTheme());

  const toggleTheme = () => {
    const next: Theme = theme === "light" ? "dark" : "light";
    setTheme(next);
    setThemeState(next);
  };

  const switchMode = async (m: "monitor" | "control") => {
    if (m === mode) return;
    setMode(m);
    setControlMotors([]);
    setCurrentMotor(null);
    await api.setMode(m);
  };

  const busLabel = status?.demo ? "demo" : status?.channel || "—";

  return (
    <header className="toolbar">
      <div className="brand">
        <span className="brand-dot" />
        DaMiao <span className="brand-sub">Studio</span>
      </div>

      <div className="mode-switch" role="tablist">
        <button className={"mode-tab " + (mode === "control" ? "active" : "")} onClick={() => switchMode("control")}>
          ◉ Control
        </button>
        <button className={"mode-tab " + (mode === "monitor" ? "active" : "")} onClick={() => switchMode("monitor")}>
          ◎ Monitor
        </button>
      </div>

      <div className="conn">
        <span className={"dot " + (connected ? "on" : "off")} />
        <span className="mono">{busLabel}</span>
        {mode === "control" ? (
          <span className="badge warn" title="active mode — transmits">active · TX</span>
        ) : (
          <span className={"badge " + (status?.listenOnly ? "ok" : "ok")} title="passive — never transmits">
            listen-only
          </span>
        )}
        {status?.error && <span className="badge err" title={status.error}>error</span>}
        {status && (
          <span className="muted small">{status.framesSeen?.toLocaleString?.() ?? 0} frames</span>
        )}
      </div>

      <div className="spacer" />

      <div className="actions">
        {PANELS.map((p) => (
          <button key={p.kind} className="btn" title={p.description} onClick={() => addWidget(p.kind)}>
            <span className="btn-icon">{p.icon}</span> {p.title}
          </button>
        ))}
        <button className="btn ghost" onClick={toggleTheme} title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}>
          {theme === "light" ? "☾" : "☀"}
        </button>
        <button className="btn ghost" onClick={resetWidgets}>Reset</button>
      </div>
    </header>
  );
}

import { useApp } from "../lib/store";
import { addPanelOfKind } from "../lib/dock";
import { PANELS } from "../panels/registry";

export default function Toolbar() {
  const connected = useApp((s) => s.connected);
  const status = useApp((s) => s.status);

  const resetLayout = () => {
    localStorage.removeItem("damiao.monitor.layout");
    localStorage.removeItem("damiao.monitor.plotConfigs");
    location.reload();
  };

  return (
    <header className="toolbar">
      <div className="brand">
        <span className="brand-dot" />
        DaMiao <span className="brand-sub">Passive Monitor</span>
      </div>

      <div className="conn">
        <span className={"dot " + (connected ? "on" : "off")} />
        <span className="mono">
          {status?.demo ? "demo" : status?.channel || "—"}
        </span>
        {status && !status.demo && (
          <span className={"badge " + (status.listenOnly ? "ok" : "warn")} title="hardware listen-only">
            {status.listenOnly ? "listen-only" : "rx (no TX)"}
          </span>
        )}
        {status?.error && <span className="badge err" title={status.error}>bus error</span>}
        {status && (
          <span className="muted small">
            {status.framesSeen.toLocaleString()} frames · +{status.feedbackOffset} fb
          </span>
        )}
      </div>

      <div className="spacer" />

      <div className="actions">
        {PANELS.map((p) => (
          <button
            key={p.kind}
            className="btn"
            title={p.description}
            onClick={() => addPanelOfKind(p.kind)}
          >
            <span className="btn-icon">{p.icon}</span> {p.title}
          </button>
        ))}
        <button className="btn ghost" onClick={resetLayout}>Reset</button>
      </div>
    </header>
  );
}

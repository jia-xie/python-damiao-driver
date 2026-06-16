import { useApp } from "../lib/store";
import { useWidgets } from "../lib/widgets";
import { PANELS } from "../panels/registry";

export default function Toolbar() {
  const connected = useApp((s) => s.connected);
  const status = useApp((s) => s.status);
  const addWidget = useWidgets((s) => s.addWidget);
  const resetWidgets = useWidgets((s) => s.resetWidgets);

  const resetLayout = () => resetWidgets();

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
            onClick={() => addWidget(p.kind)}
          >
            <span className="btn-icon">{p.icon}</span> {p.title}
          </button>
        ))}
        <button className="btn ghost" onClick={resetLayout}>Reset</button>
      </div>
    </header>
  );
}

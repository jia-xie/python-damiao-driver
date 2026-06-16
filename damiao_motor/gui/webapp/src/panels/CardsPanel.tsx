import { useApp } from "../lib/store";
import { fmt } from "../lib/format";
import { setMotorType } from "../lib/ws";

function Metric({ label, cmd, act, unit, digits = 2 }: { label: string; cmd?: number; act?: number; unit: string; digits?: number }) {
  return (
    <div className="metric">
      <div className="metric-label">{label} <span className="muted">{unit}</span></div>
      <div className="metric-values">
        <span className="metric-act">{fmt(act, digits)}</span>
        {cmd !== undefined && <span className="metric-cmd">⌖ {fmt(cmd, digits)}</span>}
      </div>
    </div>
  );
}

export default function CardsPanel() {
  const motors = useApp((s) => s.motors);
  const motorTypes = useApp((s) => s.motorTypes);

  return (
    <div className="panel cards-panel">
      {motors.length === 0 && <div className="muted center pad">Waiting for traffic…</div>}
      <div className="cards-grid">
        {motors.map((m) => (
          <div className="motor-card" key={`${m.bus}:${m.motorId}`}>
            <div className="motor-card-head">
              <span className="mono strong">Motor {m.motorId}</span>
              <span className={"status-pill " + (m.status === "ENABLED" ? "ok" : m.status === "DISABLED" ? "off" : "warn")}>
                {m.status || "—"}
              </span>
            </div>
            <div className="motor-card-sub">
              <span className="muted">{m.mode || "—"}</span>
              {motorTypes.length > 0 && (
                <select
                  className="type-select"
                  defaultValue=""
                  onChange={(e) => e.target.value && setMotorType(m.motorId, e.target.value)}
                  title="Override motor type used to scale this motor's values"
                >
                  <option value="">set type…</option>
                  {motorTypes.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              )}
            </div>
            <Metric label="Position" unit="rad" cmd={m.cmd.pos} act={m.fb.pos} digits={3} />
            <Metric label="Velocity" unit="rad/s" cmd={m.cmd.vel} act={m.fb.vel} digits={2} />
            <Metric label="Torque" unit="Nm" cmd={m.cmd.torque} act={m.fb.torque} digits={2} />
            <div className="temp-row">
              <span>MOS {fmt(m.fb.t_mos, 1)}°</span>
              <span>Rotor {fmt(m.fb.t_rotor, 1)}°</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

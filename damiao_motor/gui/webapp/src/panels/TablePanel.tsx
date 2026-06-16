import { useApp } from "../lib/store";
import { fmt } from "../lib/format";

const CMD_COLS: [string, string][] = [
  ["pos", "cmd p"],
  ["vel", "cmd v"],
  ["kp", "kp"],
  ["kd", "kd"],
  ["torque", "cmd τ"],
];
const FB_COLS: [string, string][] = [
  ["pos", "act p"],
  ["vel", "act v"],
  ["torque", "act τ"],
  ["t_mos", "Tmos"],
  ["t_rotor", "Trot"],
];

export default function TablePanel() {
  const motors = useApp((s) => s.motors);

  return (
    <div className="panel table-panel">
      <table className="motor-table">
        <thead>
          <tr>
            <th>Motor</th>
            <th>Mode</th>
            <th>Status</th>
            {CMD_COLS.map(([k, l]) => (
              <th key={"c" + k} className="cmd-col">{l}</th>
            ))}
            {FB_COLS.map(([k, l]) => (
              <th key={"f" + k}>{l}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {motors.length === 0 && (
            <tr>
              <td colSpan={3 + CMD_COLS.length + FB_COLS.length} className="muted center">
                Waiting for traffic…
              </td>
            </tr>
          )}
          {motors.map((m) => (
            <tr key={`${m.bus}:${m.motorId}`}>
              <td className="mono">m{m.motorId}</td>
              <td className="muted">{m.mode || "—"}</td>
              <td>
                <span className={"status-pill " + (m.status === "ENABLED" ? "ok" : m.status === "DISABLED" ? "off" : "warn")}>
                  {m.status || "—"}
                </span>
              </td>
              {CMD_COLS.map(([k]) => (
                <td key={"c" + k} className="mono cmd-col">{fmt(m.cmd[k], k === "kp" ? 0 : 3)}</td>
              ))}
              {FB_COLS.map(([k]) => (
                <td key={"f" + k} className="mono">{fmt(m.fb[k], k.startsWith("t_") ? 1 : 3)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

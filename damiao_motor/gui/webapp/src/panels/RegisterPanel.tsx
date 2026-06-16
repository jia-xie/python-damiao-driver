import { useEffect, useState } from "react";
import { useApp } from "../lib/store";
import { api } from "../lib/control";

const CTRL_MODES: Record<number, string> = { 1: "MIT", 2: "POS_VEL", 3: "VEL", 4: "FORCE_POS" };
const BAUDS: Record<number, string> = { 0: "125K", 1: "200K", 2: "250K", 3: "500K", 4: "1M" };

export default function RegisterPanel() {
  const appMode = useApp((s) => s.mode);
  const status = useApp((s) => s.status);
  const id = useApp((s) => s.currentMotorId);
  const regTable = useApp((s) => s.registerTable);
  const setCurrentMotor = useApp((s) => s.setCurrentMotor);
  const connected = !!status?.connected;
  const active = appMode === "control" && connected && id != null;

  const [values, setValues] = useState<Record<number, any>>({});
  const [edits, setEdits] = useState<Record<number, string>>({});
  const [msg, setMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    if (id == null) return;
    setLoading(true);
    const r = await api.getRegisters(id);
    setLoading(false);
    if (r.success) {
      setValues(r.registers || {});
      setEdits({});
    } else setMsg(r.error || "read failed");
  };
  useEffect(() => {
    if (active) load();
    else setValues({});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, active]);

  if (!active) {
    return <div className="panel control-form"><div className="muted center pad">
      {appMode !== "control" ? "Monitor mode — registers unavailable." : "Connect + select a motor."}
    </div></div>;
  }

  const parseFor = (rid: number, raw: string, dtype: string): number => {
    if (rid === 7 || rid === 8) {
      const s = raw.trim();
      return s.toLowerCase().startsWith("0x") ? parseInt(s, 16) : (parseInt(s, 16) || parseInt(s, 10));
    }
    return dtype === "float" ? parseFloat(raw) : parseInt(raw, 10);
  };

  const write = async (rid: number) => {
    const info = regTable[rid];
    const dtype = info?.data_type || "float";
    let val: number;
    if (rid === 10 || rid === 35) val = parseInt(edits[rid], 10);
    else if (rid === 9) val = parseFloat(edits[rid]);
    else val = parseFor(rid, edits[rid] ?? "", dtype);
    if (Number.isNaN(val)) { setMsg("invalid value"); return; }
    const r = await api.setRegister(id!, rid, val);
    if (r.success) {
      if (r.updated_ids?.motor_id != null) setCurrentMotor(r.updated_ids.motor_id);
      setMsg(`reg ${rid} written ✓`);
      setTimeout(load, 100);
    } else setMsg(r.error || "write failed");
  };

  const display = (rid: number, v: any): string => {
    if (rid === 9) return `${v} ms`;
    if (rid === 7 || rid === 8) return `0x${Number(v).toString(16).toUpperCase()} (${v})`;
    if (rid === 10) return CTRL_MODES[Number(v)] || String(v);
    if (rid === 35) return BAUDS[Number(v)] || String(v);
    const info = regTable[rid];
    return info?.data_type === "float" ? Number(v).toFixed(4) : String(v);
  };

  const rids = Object.keys(values).map(Number).sort((a, b) => a - b);

  return (
    <div className="panel registers-panel">
      <div className="rawlog-toolbar">
        <button className="btn small" onClick={load}>{loading ? "…" : "Refresh"}</button>
        {msg && <span className="muted small">{msg}</span>}
      </div>
      <div className="registers-body">
        <table className="motor-table reg-table">
          <thead><tr><th>Register</th><th>Value</th><th></th></tr></thead>
          <tbody>
            {rids.map((rid) => {
              const info = regTable[rid];
              const ro = info?.access === "RO";
              return (
                <tr key={rid}>
                  <td title={info?.variable}>{info?.description || `reg ${rid}`}</td>
                  <td className="mono">
                    {ro ? (
                      display(rid, values[rid])
                    ) : rid === 10 || rid === 35 ? (
                      <select value={edits[rid] ?? String(values[rid])} onChange={(e) => setEdits({ ...edits, [rid]: e.target.value })}>
                        {Object.entries(rid === 10 ? CTRL_MODES : BAUDS).map(([k, v]) => (
                          <option key={k} value={k}>{v} ({k})</option>
                        ))}
                      </select>
                    ) : (
                      <input
                        value={edits[rid] ?? (rid === 7 || rid === 8 ? `0x${Number(values[rid]).toString(16).toUpperCase()}` : String(values[rid]))}
                        onChange={(e) => setEdits({ ...edits, [rid]: e.target.value })}
                      />
                    )}
                  </td>
                  <td>{!ro && <button className="btn small" onClick={() => write(rid)}>Write</button>}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

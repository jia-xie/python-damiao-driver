import { useEffect, useRef, useState } from "react";
import { useApp } from "../lib/store";
import { api } from "../lib/control";

type Mode = "MIT" | "POS_VEL" | "VEL" | "FORCE_POS";

export default function ControlPanel() {
  const appMode = useApp((s) => s.mode);
  const status = useApp((s) => s.status);
  const id = useApp((s) => s.currentMotorId);
  const motorTypes = useApp((s) => s.motorTypes);
  const connected = !!status?.connected;
  const active = appMode === "control" && connected && id != null;

  const [mode, setMode] = useState<Mode>("MIT");
  const [pos, setPos] = useState(0);
  const [vel, setVel] = useState(0);
  const [kp, setKp] = useState(0);
  const [kd, setKd] = useState(0);
  const [tau, setTau] = useState(0);
  const [vlim, setVlim] = useState(0);
  const [tlim, setTlim] = useState(0);
  const [continuous, setContinuous] = useState(false);
  const [freq, setFreq] = useState(50);
  const [running, setRunning] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const timer = useRef<number | null>(null);

  const body = () => ({
    control_mode: mode,
    target_position: pos,
    target_velocity: vel,
    stiffness: kp,
    damping: kd,
    feedforward_torque: tau,
    velocity_limit: vlim,
    torque_limit_ratio: tlim,
  });

  const stop = () => {
    if (timer.current != null) {
      clearInterval(timer.current);
      timer.current = null;
    }
    setRunning(false);
  };

  useEffect(() => stop, []); // cleanup on unmount
  useEffect(() => {
    stop();
  }, [id, appMode]);

  const sendOnce = async () => {
    if (id == null) return;
    const r = await api.command(id, body());
    if (!r.success) {
      setMsg(r.error || "command failed");
      stop();
    }
  };
  const onSend = () => {
    if (!continuous) {
      sendOnce();
    } else if (running) {
      stop();
    } else {
      setRunning(true);
      setMsg(null);
      sendOnce();
      const ms = 1000 / Math.max(1, Math.min(1000, freq));
      timer.current = window.setInterval(sendOnce, ms);
    }
  };

  const act = async (fn: () => Promise<any>, label: string) => {
    const r = await fn();
    setMsg(r?.success ? `${label} ✓` : `${label} failed: ${r?.error || ""}`);
  };

  if (!active) {
    return (
      <div className="panel control-form">
        <div className="muted center pad">
          {appMode !== "control"
            ? "Monitor mode — switch to Control to drive motors."
            : !connected
            ? "Connect to a bus (Connection widget)."
            : "Select a motor in the Connection widget."}
        </div>
      </div>
    );
  }

  const showPos = mode !== "VEL";
  const showMit = mode === "MIT";
  const showForce = mode === "FORCE_POS";
  const velLabel = mode === "POS_VEL" || showForce ? "Vel limit" : "Velocity";

  return (
    <div className="panel control-form">
      <div className="form-row">
        <label>Mode</label>
        <select value={mode} onChange={(e) => setMode(e.target.value as Mode)}>
          <option>MIT</option>
          <option>POS_VEL</option>
          <option>VEL</option>
          <option>FORCE_POS</option>
        </select>
      </div>
      {showPos && (
        <div className="form-row"><label>Position</label>
          <input type="number" step="0.001" value={pos} onChange={(e) => setPos(+e.target.value)} /></div>
      )}
      <div className="form-row"><label>{velLabel}</label>
        <input type="number" step="0.01" value={mode === "FORCE_POS" ? vlim : vel}
          onChange={(e) => (mode === "FORCE_POS" ? setVlim(+e.target.value) : setVel(+e.target.value))} /></div>
      {showMit && <>
        <div className="form-row"><label>Stiffness Kp</label>
          <input type="number" step="0.1" value={kp} onChange={(e) => setKp(+e.target.value)} /></div>
        <div className="form-row"><label>Damping Kd</label>
          <input type="number" step="0.01" value={kd} onChange={(e) => setKd(+e.target.value)} /></div>
        <div className="form-row"><label>Torque</label>
          <input type="number" step="0.01" value={tau} onChange={(e) => setTau(+e.target.value)} /></div>
      </>}
      {showForce && (
        <div className="form-row"><label>Torque limit</label>
          <input type="number" step="0.01" min="0" max="1" value={tlim} onChange={(e) => setTlim(+e.target.value)} /></div>
      )}

      <div className="form-actions">
        <button className="btn ok" onClick={() => act(() => api.enable(id), "Enable")}>Enable</button>
        <button className="btn danger" onClick={() => { stop(); act(() => api.disable(id), "Disable"); }}>Disable</button>
      </div>

      <div className="form-actions">
        <button className={"btn " + (running ? "danger" : "primary")} onClick={onSend}>
          {continuous ? (running ? "Stop" : "Start") : "Send"}
        </button>
        <label className="toggle">
          <input type="checkbox" checked={continuous} onChange={(e) => { setContinuous(e.target.checked); stop(); }} />
          continuous
        </label>
        {continuous && (
          <input className="freq" type="number" min="1" max="1000" value={freq}
            onChange={(e) => setFreq(+e.target.value)} title="Hz" />
        )}
      </div>

      <div className="form-actions wrap">
        <button className="btn" onClick={() => act(() => api.setZero(id), "Set zero")}>Set Zero</button>
        <button className="btn" onClick={() => act(() => api.clearError(id), "Clear error")}>Clear Err</button>
        <button className="btn" onClick={() => act(() => api.storeParams(id), "Store")}>Store</button>
      </div>
      <div className="form-row">
        <label>Type</label>
        <select defaultValue="" onChange={(e) => e.target.value && act(() => api.setMotorType(id, e.target.value), "Type")}>
          <option value="">set…</option>
          {motorTypes.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>
      {msg && <div className="form-msg">{msg}</div>}
    </div>
  );
}

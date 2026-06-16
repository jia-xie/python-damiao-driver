import { useEffect, useState } from "react";
import { useApp } from "../lib/store";
import { api } from "../lib/control";

export default function ConnectionPanel() {
  const mode = useApp((s) => s.mode);
  const status = useApp((s) => s.status);
  const controlMotors = useApp((s) => s.controlMotors);
  const currentMotorId = useApp((s) => s.currentMotorId);
  const setControlMotors = useApp((s) => s.setControlMotors);
  const setCurrentMotor = useApp((s) => s.setCurrentMotor);
  const motorTypes = useApp((s) => s.motorTypes);

  const [bustype, setBustype] = useState("socketcan");
  const [channel, setChannel] = useState("can0");
  const [bitrate, setBitrate] = useState(1000000);
  const [ifaces, setIfaces] = useState<string[]>([]);
  const [motorType, setMotorType] = useState("DM4310");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const connected = !!status?.connected;

  useEffect(() => {
    api.platform().then((p) => {
      if (p?.success) {
        setBustype(p.default_bustype);
        setChannel(p.default_channel);
      }
    });
  }, []);
  useEffect(() => {
    api.canInterfaces(bustype).then((d) => setIfaces(d?.interfaces || []));
  }, [bustype]);

  const connect = async () => {
    setBusy(true);
    setErr(null);
    const body: any = { channel, bustype };
    if (bustype === "gs_usb") body.bitrate = bitrate;
    if (mode === "control") body.motor_type = motorType;
    const r = await api.connect(body);
    setBusy(false);
    if (r.success) {
      const motors = r.motors || [];
      setControlMotors(motors);
      if (motors.length) setCurrentMotor(motors[0].id);
    } else {
      setErr(r.error || "Connect failed");
    }
  };
  const disconnect = async () => {
    await api.disconnect();
    setControlMotors([]);
    setCurrentMotor(null);
  };
  const rescan = async () => {
    setBusy(true);
    const r = await api.scan(motorType);
    setBusy(false);
    if (r.success) {
      setControlMotors(r.motors || []);
      if ((r.motors || []).length) setCurrentMotor(r.motors[0].id);
    } else setErr(r.error || "Scan failed");
  };

  return (
    <div className="panel control-form">
      <div className="form-row">
        <label>Bus</label>
        <select value={bustype} onChange={(e) => setBustype(e.target.value)} disabled={connected}>
          <option value="socketcan">socketcan</option>
          <option value="gs_usb">gs_usb</option>
        </select>
      </div>
      <div className="form-row">
        <label>Channel</label>
        <input list="ifaces" value={channel} onChange={(e) => setChannel(e.target.value)} disabled={connected} />
        <datalist id="ifaces">
          {ifaces.map((i) => <option key={i} value={i} />)}
        </datalist>
      </div>
      {bustype === "gs_usb" && (
        <div className="form-row">
          <label>Bitrate</label>
          <input type="number" value={bitrate} onChange={(e) => setBitrate(Number(e.target.value))} disabled={connected} />
        </div>
      )}
      {mode === "control" && (
        <div className="form-row">
          <label>Motor type</label>
          <select value={motorType} onChange={(e) => setMotorType(e.target.value)}>
            {motorTypes.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
      )}
      <div className="form-actions">
        {!connected ? (
          <button className="btn primary" onClick={connect} disabled={busy}>
            {busy ? "Connecting…" : "Connect"}
          </button>
        ) : (
          <button className="btn" onClick={disconnect}>Disconnect</button>
        )}
        {mode === "control" && connected && (
          <button className="btn" onClick={rescan} disabled={busy}>Rescan</button>
        )}
      </div>

      {mode === "control" && connected && (
        <div className="form-row">
          <label>Motor</label>
          <select
            value={currentMotorId ?? ""}
            onChange={(e) => setCurrentMotor(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">select…</option>
            {controlMotors.map((m) => (
              <option key={m.id} value={m.id}>
                Motor {m.id} (0x{m.id.toString(16).toUpperCase()})
              </option>
            ))}
          </select>
        </div>
      )}
      {mode === "monitor" && (
        <div className="muted small" style={{ marginTop: 6 }}>
          Monitor mode: listening only. Switch to Control to drive motors.
        </div>
      )}
      {err && <div className="form-error">{err}</div>}
    </div>
  );
}

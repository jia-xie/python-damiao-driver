import { useMemo, useState } from "react";
import { useApp } from "../lib/store";
import { FIELD_ORDER } from "../lib/format";
import SignalChip from "./SignalChip";
import type { SignalDescriptor } from "../lib/types";

function sortSignals(sigs: SignalDescriptor[]): SignalDescriptor[] {
  return [...sigs].sort((a, b) => {
    if (a.source !== b.source) return a.source === "cmd" ? -1 : 1;
    const ai = FIELD_ORDER.indexOf(a.field);
    const bi = FIELD_ORDER.indexOf(b.field);
    return (ai < 0 ? 99 : ai) - (bi < 0 ? 99 : bi);
  });
}

export default function SignalSidebar() {
  const signals = useApp((s) => s.signals);
  const status = useApp((s) => s.status);
  const [filter, setFilter] = useState("");

  const byMotor = useMemo(() => {
    const map = new Map<number, SignalDescriptor[]>();
    for (const s of signals) {
      if (filter && !s.id.toLowerCase().includes(filter.toLowerCase())) continue;
      const arr = map.get(s.motorId) || [];
      arr.push(s);
      map.set(s.motorId, arr);
    }
    return Array.from(map.entries()).sort((a, b) => a[0] - b[0]);
  }, [signals, filter]);

  return (
    <aside className="sidebar">
      <div className="sidebar-head">
        <div className="sidebar-title">Signals</div>
        <input
          className="filter"
          placeholder="filter…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>

      <div className="sidebar-body">
        {byMotor.length === 0 && (
          <div className="muted pad">
            {status?.error ? "Bus error — see top bar." : "No signals yet. Start a controller on the bus (or run --demo)."}
          </div>
        )}
        {byMotor.map(([motorId, sigs]) => (
          <div className="motor-group" key={motorId}>
            <div className="motor-group-title">Motor {motorId}</div>
            <div className="chips">
              {sortSignals(sigs).map((s) => (
                <SignalChip key={s.id} sig={s} />
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="sidebar-foot muted">
        Drag a signal onto a plot. Drop <b>cmd</b> onto its <b>fb</b> plot to overlay.
      </div>
    </aside>
  );
}

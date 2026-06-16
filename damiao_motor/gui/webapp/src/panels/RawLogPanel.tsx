import { useEffect, useRef, useState } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";

import { getRawFrames, onRawFrames, wantRaw } from "../lib/dataStore";
import type { RawFrame } from "../lib/types";

const SHORT: Record<string, string> = {
  pos: "p",
  vel: "v",
  torque: "τ",
  kp: "kp",
  kd: "kd",
  vel_limit: "vlim",
  torque_limit: "τlim",
  t_mos: "Tm",
  t_rotor: "Tr",
};
const SUMMARY_ORDER = ["pos", "vel", "torque", "kp", "kd", "t_mos", "t_rotor"];

function fieldsSummary(f: RawFrame): string {
  const parts: string[] = [];
  for (const k of SUMMARY_ORDER) {
    if (k in f.fields) parts.push(`${SHORT[k] || k} ${f.fields[k].toFixed(2)}`);
  }
  return parts.join("   ") || f.note || "";
}

function fmtTime(t: number): string {
  const d = new Date(t * 1000);
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  const ss = String(d.getSeconds()).padStart(2, "0");
  const ms = String(Math.floor((t % 1) * 1000)).padStart(3, "0");
  return `${hh}:${mm}:${ss}.${ms}`;
}

export default function RawLogPanel() {
  const [, force] = useState(0);
  const [paused, setPaused] = useState(false);
  const parentRef = useRef<HTMLDivElement | null>(null);
  const framesRef = useRef<RawFrame[]>([]);

  useEffect(() => {
    wantRaw(true);
    const off = onRawFrames(() => {
      if (!paused) {
        framesRef.current = getRawFrames();
        force((x) => x + 1);
      }
    });
    return () => {
      wantRaw(false);
      off();
    };
  }, [paused]);

  const frames = framesRef.current;
  const rowVirt = useVirtualizer({
    count: frames.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 22,
    overscan: 12,
  });

  // auto-scroll to bottom unless paused
  useEffect(() => {
    if (!paused && frames.length) rowVirt.scrollToIndex(frames.length - 1);
  }, [frames.length, paused, rowVirt]);

  return (
    <div className="panel rawlog-panel">
      <div className="rawlog-toolbar">
        <button className={paused ? "btn small" : "btn small active"} onClick={() => setPaused((p) => !p)}>
          {paused ? "Resume" : "Pause"}
        </button>
        <span className="muted">{frames.length} frames</span>
      </div>
      <div className="rawlog-body" ref={parentRef}>
        {/* sticky header lives in the same scroll container as the rows, sharing the
            exact grid + padding so columns line up perfectly */}
        <div className="rawlog-head">
          <span className="c-t">time</span>
          <span className="c-arb">arb</span>
          <span className="c-m">motor</span>
          <span className="c-k">kind</span>
          <span className="c-f">decoded</span>
          <span className="c-r">raw</span>
        </div>
        <div style={{ height: rowVirt.getTotalSize(), position: "relative" }}>
          {rowVirt.getVirtualItems().map((vi) => {
            const f = frames[vi.index];
            return (
              <div
                key={f.seq}
                className={"rawlog-row k-" + f.kind}
                style={{ transform: `translateY(${vi.start}px)` }}
              >
                <span className="c-t mono">{fmtTime(f.t)}</span>
                <span className="c-arb mono">0x{f.arb.toString(16).toUpperCase()}</span>
                <span className="c-m mono">m{f.motorId}</span>
                <span className="c-k">{f.mode || f.kind}</span>
                <span className="c-f mono">{fieldsSummary(f)}</span>
                <span className="c-r mono dim">{f.raw}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

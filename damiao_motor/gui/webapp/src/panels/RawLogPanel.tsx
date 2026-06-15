import { useEffect, useRef, useState } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";

import { getRawFrames, onRawFrames, wantRaw } from "../lib/dataStore";
import type { RawFrame } from "../lib/types";

function fieldsSummary(f: RawFrame): string {
  const keys = Object.keys(f.fields);
  if (!keys.length) return f.note || "";
  return keys
    .slice(0, 4)
    .map((k) => `${k}=${f.fields[k]}`)
    .join("  ");
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
        <div className="rawlog-head">
          <span className="c-t">t</span>
          <span className="c-arb">arb</span>
          <span className="c-m">motor</span>
          <span className="c-k">kind</span>
          <span className="c-f">decoded</span>
          <span className="c-r">raw</span>
        </div>
      </div>
      <div className="rawlog-body" ref={parentRef}>
        <div style={{ height: rowVirt.getTotalSize(), position: "relative" }}>
          {rowVirt.getVirtualItems().map((vi) => {
            const f = frames[vi.index];
            return (
              <div
                key={f.seq}
                className={"rawlog-row k-" + f.kind}
                style={{ transform: `translateY(${vi.start}px)` }}
              >
                <span className="c-t mono">{f.t.toFixed(3)}</span>
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

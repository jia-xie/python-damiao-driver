import { useEffect, useMemo, useRef } from "react";
import { useDroppable } from "@dnd-kit/core";
import uPlot from "uplot";
import "uplot/dist/uPlot.min.css";

import { useApp } from "../lib/store";
import {
  appendBatch,
  readSeries,
  subscribeSignal,
  unsubscribeSignal,
} from "../lib/dataStore";
import { fetchSnapshot } from "../lib/ws";
import { isCmd, shortSignal, seriesStyle } from "../lib/format";

const MAX_X = 2000; // cap aligned x points per frame

/** Forward-fill align several signals onto the union of their timestamps. */
function buildAligned(ids: string[], sinceT: number): uPlot.AlignedData {
  const series = ids.map((id) => readSeries(id, sinceT));
  const tset = new Set<number>();
  for (const s of series) for (let i = 0; i < s.t.length; i++) tset.add(s.t[i]);
  let xs = Array.from(tset).sort((a, b) => a - b);
  if (xs.length > MAX_X) {
    const stride = Math.ceil(xs.length / MAX_X);
    xs = xs.filter((_, i) => i % stride === 0);
  }
  const cols: (number | null)[][] = [xs];
  for (const s of series) {
    const col: (number | null)[] = new Array(xs.length).fill(null);
    let j = 0;
    let last: number | null = null;
    for (let i = 0; i < xs.length; i++) {
      while (j < s.t.length && s.t[j] <= xs[i]) {
        last = s.v[j];
        j++;
      }
      col[i] = last;
    }
    cols.push(col);
  }
  return cols as unknown as uPlot.AlignedData;
}

export default function PlotPanel({ panelId }: { panelId: string }) {
  const ensurePlot = useApp((s) => s.ensurePlot);
  const removeSignalFromPlot = useApp((s) => s.removeSignalFromPlot);
  const setPlotConfig = useApp((s) => s.setPlotConfig);
  const cfg = useApp((s) => s.plotConfigs[panelId]);
  const signalsMeta = useApp((s) => s.signals);

  useEffect(() => {
    ensurePlot(panelId);
  }, [panelId, ensurePlot]);

  const signals = cfg?.signals ?? [];
  const duration = cfg?.duration ?? 10;
  const sigKey = signals.join("|");

  const { setNodeRef, isOver } = useDroppable({ id: `plot:${panelId}`, data: { panelId } });
  const hostRef = useRef<HTMLDivElement | null>(null);
  const plotRef = useRef<uPlot | null>(null);
  const maxTRef = useRef<number>(0);

  // (re)create the uPlot instance whenever the set of signals changes
  useEffect(() => {
    if (!hostRef.current) return;
    const el = hostRef.current;

    const descById = new Map(signalsMeta.map((s) => [s.id, s]));
    const seriesCfg: uPlot.Series[] = [
      { label: "t" },
      ...signals.map((id) => {
        const d = descById.get(id);
        const style = d ? seriesStyle(d) : { stroke: "#8b949e", width: 1.5 };
        return {
          label: shortSignal(id),
          stroke: style.stroke,
          width: style.width,
          points: { show: false },
        } as uPlot.Series;
      }),
    ];

    const opts: uPlot.Options = {
      width: el.clientWidth || 400,
      height: el.clientHeight || 220,
      legend: { show: false },
      series: seriesCfg,
      cursor: { y: false, points: { show: true } },
      scales: { x: { time: false } },
      axes: [
        {
          stroke: "#8b949e",
          grid: { stroke: "rgba(139,148,158,0.12)" },
          ticks: { stroke: "rgba(139,148,158,0.2)" },
          values: (_u, vals) => vals.map((v) => (v - maxTRef.current).toFixed(1) + "s"),
        },
        {
          stroke: "#8b949e",
          grid: { stroke: "rgba(139,148,158,0.12)" },
          ticks: { stroke: "rgba(139,148,158,0.2)" },
        },
      ],
    };

    const plot = new uPlot(opts, [[], ...signals.map(() => [])] as unknown as uPlot.AlignedData, el);
    plotRef.current = plot;

    const ro = new ResizeObserver(() => {
      plot.setSize({ width: el.clientWidth, height: el.clientHeight });
    });
    ro.observe(el);

    return () => {
      ro.disconnect();
      plot.destroy();
      plotRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sigKey, signalsMeta.length]);

  // subscribe to streams + backfill history when the signal set changes
  useEffect(() => {
    if (!signals.length) return;
    signals.forEach(subscribeSignal);
    let cancelled = false;
    fetchSnapshot(signals, 1200).then((snap) => {
      if (cancelled) return;
      for (const [id, pts] of Object.entries(snap)) appendBatch(id, pts);
    });
    return () => {
      cancelled = true;
      signals.forEach(unsubscribeSignal);
    };
  }, [sigKey]);

  // rAF render loop: pull from the ring buffers and push into uPlot
  useEffect(() => {
    let raf = 0;
    const tick = () => {
      const plot = plotRef.current;
      if (plot && signals.length) {
        // find latest t across signals to anchor the window
        let maxT = 0;
        for (const id of signals) {
          const s = readSeries(id);
          if (s.t.length) maxT = Math.max(maxT, s.t[s.t.length - 1]);
        }
        maxTRef.current = maxT;
        const data = buildAligned(signals, maxT - duration);
        plot.setData(data, false);
        plot.setScale("x", { min: maxT - duration, max: maxT });
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [sigKey, duration]);

  const descById = useMemo(() => new Map(signalsMeta.map((s) => [s.id, s])), [signalsMeta]);

  return (
    <div className="panel plot-panel" ref={setNodeRef}>
      <div className="plot-toolbar">
        <span className="muted">window</span>
        <select
          value={duration}
          onChange={(e) => setPlotConfig(panelId, { duration: Number(e.target.value) })}
        >
          {[5, 10, 20, 30, 60].map((d) => (
            <option key={d} value={d}>
              {d}s
            </option>
          ))}
        </select>
        <div className="legend">
          {signals.map((id) => {
            const d = descById.get(id);
            const style = d ? seriesStyle(d) : { stroke: "#555" };
            return (
              <span className="legend-chip" key={id}>
                <span
                  className="legend-swatch"
                  style={{ background: style.stroke, opacity: isCmd(id) ? 0.9 : 1 }}
                />
                {shortSignal(id)}
                <button className="legend-x" onClick={() => removeSignalFromPlot(panelId, id)}>×</button>
              </span>
            );
          })}
        </div>
      </div>
      <div className={"plot-host" + (isOver ? " drop-over" : "")} ref={hostRef}>
        {signals.length === 0 && (
          <div className="drop-hint">Drag signals here to plot — drop cmd onto fb to overlay</div>
        )}
      </div>
    </div>
  );
}

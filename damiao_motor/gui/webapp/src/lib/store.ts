/** Low-frequency app state (registry, status, motor views, panel configs, layout). */

import { create } from "zustand";
import type { MotorView, Pair, PanelKind, ServerStatus, SignalDescriptor } from "./types";

export interface PlotConfig {
  signals: string[];
  duration: number; // seconds visible
}

// Persistence helpers must be defined BEFORE the store, because the store initializer
// calls loadPlotConfigs() synchronously (a `const` declared later would be in the TDZ).
const PLOT_KEY = "damiao.monitor.plotConfigs";
export function loadPlotConfigs(): Record<string, PlotConfig> {
  try {
    return JSON.parse(localStorage.getItem(PLOT_KEY) || "{}");
  } catch {
    return {};
  }
}
export function persistPlotConfigs(cfgs: Record<string, PlotConfig>) {
  try {
    localStorage.setItem(PLOT_KEY, JSON.stringify(cfgs));
  } catch {
    /* ignore quota */
  }
}

interface AppState {
  connected: boolean;
  status: ServerStatus | null;
  signals: SignalDescriptor[];
  pairs: Pair[];
  motors: MotorView[];
  motorTypes: string[];
  // per-panel plot configs (signals shown), persisted alongside the dock layout
  plotConfigs: Record<string, PlotConfig>;

  setConnected: (c: boolean) => void;
  setStatus: (s: ServerStatus) => void;
  setMeta: (signals: SignalDescriptor[], pairs: Pair[]) => void;
  setMotors: (m: MotorView[]) => void;
  setMotorTypes: (t: string[]) => void;

  ensurePlot: (id: string) => void;
  setPlotConfig: (id: string, cfg: Partial<PlotConfig>) => void;
  addSignalToPlot: (id: string, signalId: string) => void;
  removeSignalFromPlot: (id: string, signalId: string) => void;
  dropPlot: (id: string) => void;
}

export const useApp = create<AppState>((set, get) => ({
  connected: false,
  status: null,
  signals: [],
  pairs: [],
  motors: [],
  motorTypes: [],
  plotConfigs: loadPlotConfigs(), // hydrate synchronously to avoid effect-ordering races

  setConnected: (c) => set({ connected: c }),
  setStatus: (s) => set({ status: s }),
  setMeta: (signals, pairs) => set({ signals, pairs }),
  setMotors: (motors) => set({ motors }),
  setMotorTypes: (motorTypes) => set({ motorTypes }),

  ensurePlot: (id) =>
    set((st) =>
      st.plotConfigs[id]
        ? st
        : { plotConfigs: { ...st.plotConfigs, [id]: { signals: [], duration: 10 } } }
    ),
  setPlotConfig: (id, cfg) =>
    set((st) => ({
      plotConfigs: {
        ...st.plotConfigs,
        [id]: { ...(st.plotConfigs[id] || { signals: [], duration: 10 }), ...cfg },
      },
    })),
  addSignalToPlot: (id, signalId) =>
    set((st) => {
      const cur = st.plotConfigs[id] || { signals: [], duration: 10 };
      if (cur.signals.includes(signalId)) return st;
      return {
        plotConfigs: { ...st.plotConfigs, [id]: { ...cur, signals: [...cur.signals, signalId] } },
      };
    }),
  removeSignalFromPlot: (id, signalId) =>
    set((st) => {
      const cur = st.plotConfigs[id];
      if (!cur) return st;
      return {
        plotConfigs: {
          ...st.plotConfigs,
          [id]: { ...cur, signals: cur.signals.filter((s) => s !== signalId) },
        },
      };
    }),
  dropPlot: (id) =>
    set((st) => {
      const next = { ...st.plotConfigs };
      delete next[id];
      return { plotConfigs: next };
    }),
}));

// persist plot configs whenever they change (dock layout persisted by the Dock component)
useApp.subscribe((st) => persistPlotConfigs(st.plotConfigs));

export const PANEL_TITLES: Record<PanelKind, string> = {
  plot: "Plot",
  table: "Motor Table",
  cards: "Motor Cards",
  rawlog: "Raw CAN Log",
};

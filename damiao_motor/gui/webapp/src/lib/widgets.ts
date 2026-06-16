/** Free-form widget canvas state: a list of widgets with grid geometry, persisted. */

import { create } from "zustand";

export interface Widget {
  id: string;
  kind: string; // panel kind from panels/registry
  x: number;
  y: number;
  w: number;
  h: number;
}

const KEY = "damiao.monitor.widgets.v3";

function load(): Widget[] | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const arr = JSON.parse(raw);
    return Array.isArray(arr) && arr.length ? arr : null;
  } catch {
    return null;
  }
}

function persist(widgets: Widget[]) {
  try {
    localStorage.setItem(KEY, JSON.stringify(widgets));
  } catch {
    /* ignore quota */
  }
}

const DEFAULT_WIDGETS: Widget[] = [
  { id: "connection-1", kind: "connection", x: 0, y: 0, w: 3, h: 4 },
  { id: "control-1", kind: "control", x: 0, y: 4, w: 3, h: 8 },
  { id: "plot-1", kind: "plot", x: 3, y: 0, w: 6, h: 6 },
  { id: "cards-1", kind: "cards", x: 9, y: 0, w: 3, h: 6 },
  { id: "table-1", kind: "table", x: 3, y: 6, w: 6, h: 6 },
  { id: "registers-1", kind: "registers", x: 9, y: 6, w: 3, h: 6 },
];

let counter = 1;

interface WidgetState {
  widgets: Widget[];
  addWidget: (kind: string) => string;
  removeWidget: (id: string) => void;
  updateGeom: (geoms: { id: string; x: number; y: number; w: number; h: number }[]) => void;
  resetWidgets: () => void;
}

export const useWidgets = create<WidgetState>((set, get) => ({
  widgets: load() || DEFAULT_WIDGETS,

  addWidget: (kind) => {
    counter += 1;
    const id = `${kind}-${Date.now().toString(36)}-${counter}`;
    // place new widget at the bottom; GridStack will reflow/auto-position
    const maxY = get().widgets.reduce((m, w) => Math.max(m, w.y + w.h), 0);
    const widget: Widget = { id, kind, x: 0, y: maxY, w: 6, h: 5 };
    const next = [...get().widgets, widget];
    persist(next);
    set({ widgets: next });
    return id;
  },

  removeWidget: (id) => {
    const next = get().widgets.filter((w) => w.id !== id);
    persist(next);
    set({ widgets: next });
  },

  updateGeom: (geoms) => {
    const byId = new Map(geoms.map((g) => [g.id, g]));
    const next = get().widgets.map((w) => {
      const g = byId.get(w.id);
      return g ? { ...w, x: g.x, y: g.y, w: g.w, h: g.h } : w;
    });
    persist(next);
    set({ widgets: next });
  },

  resetWidgets: () => {
    try {
      localStorage.removeItem(KEY);
      localStorage.removeItem("damiao.monitor.plotConfigs");
    } catch {
      /* ignore */
    }
    set({ widgets: DEFAULT_WIDGETS.map((w) => ({ ...w })) });
  },
}));

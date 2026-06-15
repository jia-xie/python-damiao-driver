import type { DockviewApi } from "dockview";
import type { PanelKind } from "./types";
import { PANEL_TITLES } from "./store";

let api: DockviewApi | null = null;
const counters: Record<string, number> = {};

export function setDockApi(a: DockviewApi | null) {
  api = a;
}
export function getDockApi(): DockviewApi | null {
  return api;
}

export function addPanelOfKind(kind: PanelKind) {
  if (!api) return;
  counters[kind] = (counters[kind] || 0) + 1;
  const id = `${kind}-${Date.now().toString(36)}-${counters[kind]}`;
  api.addPanel({
    id,
    component: kind,
    title: `${PANEL_TITLES[kind]} ${counters[kind]}`,
  });
}

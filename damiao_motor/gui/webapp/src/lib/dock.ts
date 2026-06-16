import type { DockviewApi } from "dockview";
import { PANEL_BY_KIND } from "../panels/registry";

let api: DockviewApi | null = null;
const counters: Record<string, number> = {};

export function setDockApi(a: DockviewApi | null) {
  api = a;
}
export function getDockApi(): DockviewApi | null {
  return api;
}

export function addPanelOfKind(kind: string) {
  if (!api) return;
  const def = PANEL_BY_KIND[kind];
  if (!def) return;
  counters[kind] = (counters[kind] || 0) + 1;
  const id = `${kind}-${Date.now().toString(36)}-${counters[kind]}`;
  api.addPanel({ id, component: kind, title: `${def.title} ${counters[kind]}` });
}

/**
 * Panel registry — the single source of truth for panel types.
 *
 * To add a new view, add ONE entry here: its kind, title, icon, and how to render it.
 * The dock component map, the toolbar "add panel" buttons, the default layout, and panel
 * titling are all derived from this list, so nothing else needs editing.
 */

import PlotPanel from "./PlotPanel";
import TablePanel from "./TablePanel";
import CardsPanel from "./CardsPanel";
import RawLogPanel from "./RawLogPanel";

export interface PanelDef {
  kind: string;
  title: string;
  icon: string;
  description: string;
  /** Render the panel body given its dockview panel id. */
  render: (panelId: string) => JSX.Element;
}

export const PANELS: PanelDef[] = [
  {
    kind: "plot",
    title: "Plot",
    icon: "〜",
    description: "Time-series chart; drag signals onto it (cmd over fb to overlay).",
    render: (id) => <PlotPanel panelId={id} />,
  },
  {
    kind: "table",
    title: "Motor Table",
    icon: "▦",
    description: "One row per motor: commanded vs actual.",
    render: () => <TablePanel />,
  },
  {
    kind: "cards",
    title: "Motor Cards",
    icon: "▢",
    description: "Per-motor cards/gauges with big readouts.",
    render: () => <CardsPanel />,
  },
  {
    kind: "rawlog",
    title: "Raw CAN Log",
    icon: "≣",
    description: "Scrolling decoded frame log.",
    render: () => <RawLogPanel />,
  },
];

export const PANEL_BY_KIND: Record<string, PanelDef> = Object.fromEntries(
  PANELS.map((p) => [p.kind, p])
);

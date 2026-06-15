import { useCallback } from "react";
import {
  DockviewReact,
  type DockviewReadyEvent,
  type IDockviewPanelProps,
} from "dockview";
import "dockview/dist/styles/dockview.css";

import PlotPanel from "../panels/PlotPanel";
import TablePanel from "../panels/TablePanel";
import CardsPanel from "../panels/CardsPanel";
import RawLogPanel from "../panels/RawLogPanel";
import { setDockApi } from "../lib/dock";

const LAYOUT_KEY = "damiao.monitor.layout";

const components = {
  plot: (props: IDockviewPanelProps) => <PlotPanel panelId={props.api.id} />,
  table: () => <TablePanel />,
  cards: () => <CardsPanel />,
  rawlog: () => <RawLogPanel />,
};

function defaultLayout(api: DockviewReadyEvent["api"]) {
  api.addPanel({ id: "plot-1", component: "plot", title: "Plot 1" });
  api.addPanel({
    id: "cards-1",
    component: "cards",
    title: "Motor Cards",
    position: { referencePanel: "plot-1", direction: "right" },
  });
  api.addPanel({
    id: "table-1",
    component: "table",
    title: "Motor Table",
    position: { referencePanel: "plot-1", direction: "below" },
  });
  api.addPanel({
    id: "raw-1",
    component: "rawlog",
    title: "Raw CAN Log",
    position: { referencePanel: "table-1", direction: "within" },
  });
}

export default function Dock() {
  const onReady = useCallback((event: DockviewReadyEvent) => {
    const { api } = event;
    setDockApi(api);

    const saved = localStorage.getItem(LAYOUT_KEY);
    let restored = false;
    if (saved) {
      try {
        api.fromJSON(JSON.parse(saved));
        restored = true;
      } catch {
        restored = false;
      }
    }
    if (!restored) defaultLayout(api);

    api.onDidLayoutChange(() => {
      try {
        localStorage.setItem(LAYOUT_KEY, JSON.stringify(api.toJSON()));
      } catch {
        /* ignore quota */
      }
    });
  }, []);

  return (
    <DockviewReact
      className="dockview-theme-abyss"
      components={components}
      onReady={onReady}
    />
  );
}

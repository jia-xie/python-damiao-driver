import { useEffect, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";

import Toolbar from "./components/Toolbar";
import SignalSidebar from "./components/SignalSidebar";
import Dock from "./components/Dock";
import { useApp } from "./lib/store";
import { connectWs, fetchMotorTypes } from "./lib/ws";
import { shortSignal } from "./lib/format";

export default function App() {
  const addSignalToPlot = useApp((s) => s.addSignalToPlot);
  const setMotorTypes = useApp((s) => s.setMotorTypes);
  const [dragLabel, setDragLabel] = useState<string | null>(null);

  // a 4 px activation distance so clicks on chips don't accidentally start drags
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));

  useEffect(() => {
    // store hydrates plot configs synchronously at creation; just connect + load types
    connectWs();
    fetchMotorTypes().then(setMotorTypes);
  }, [setMotorTypes]);

  const onDragStart = (e: DragStartEvent) => {
    const sid = e.active.data.current?.signalId as string | undefined;
    setDragLabel(sid ? shortSignal(sid) : null);
  };
  const onDragEnd = (e: DragEndEvent) => {
    setDragLabel(null);
    const sid = e.active.data.current?.signalId as string | undefined;
    const overId = e.over?.id?.toString() || "";
    if (sid && overId.startsWith("plot:")) {
      const panelId = e.over!.data.current?.panelId as string;
      addSignalToPlot(panelId, sid);
    }
  };

  return (
    <DndContext sensors={sensors} onDragStart={onDragStart} onDragEnd={onDragEnd}>
      <div className="app">
        <Toolbar />
        <div className="body">
          <SignalSidebar />
          <main className="dock-host">
            <Dock />
          </main>
        </div>
      </div>
      <DragOverlay dropAnimation={null}>
        {dragLabel ? <div className="drag-ghost">{dragLabel}</div> : null}
      </DragOverlay>
    </DndContext>
  );
}

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
import Canvas from "./components/Canvas";
import { useApp } from "./lib/store";
import { connectWs, fetchMotorTypes } from "./lib/ws";
import { shortSignal } from "./lib/format";
import { api } from "./lib/control";

export default function App() {
  const addSignalToPlot = useApp((s) => s.addSignalToPlot);
  const setMotorTypes = useApp((s) => s.setMotorTypes);
  const setMode = useApp((s) => s.setMode);
  const setStatus = useApp((s) => s.setStatus);
  const setRegisterTable = useApp((s) => s.setRegisterTable);
  const [dragLabel, setDragLabel] = useState<string | null>(null);

  // a 4 px activation distance so clicks on chips don't accidentally start drags
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));

  useEffect(() => {
    // store hydrates plot configs synchronously at creation; just connect + load metadata
    connectWs();
    fetchMotorTypes().then(setMotorTypes);
    api.status().then((s) => {
      if (s?.mode) setMode(s.mode);
      setStatus(s);
    });
    api.registerTable().then((d) => {
      if (d?.registers) {
        const t: Record<number, any> = {};
        for (const r of d.registers) t[r.rid] = r;
        setRegisterTable(t);
      }
    });
  }, [setMotorTypes, setMode, setStatus, setRegisterTable]);

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
          <main className="canvas-host">
            <Canvas />
          </main>
        </div>
      </div>
      <DragOverlay dropAnimation={null}>
        {dragLabel ? <div className="drag-ghost">{dragLabel}</div> : null}
      </DragOverlay>
    </DndContext>
  );
}

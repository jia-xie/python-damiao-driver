/** WebSocket client: feeds the data store + zustand app state. Auto-reconnects. */

import {
  appendBatch,
  currentSubscriptions,
  isRawWanted,
  onRawWantChanged,
  onSubscriptionsChanged,
  pushRawFrames,
} from "./dataStore";
import { useApp } from "./store";
import type { MotorView, Pair, RawFrame, ServerStatus, SignalDescriptor } from "./types";

let ws: WebSocket | null = null;
let reconnectTimer: number | null = null;

function wsUrl(): string {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${location.host}/api/monitor/stream`;
}

function sendSubscribe() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "subscribe", signals: currentSubscriptions() }));
  }
}
function sendRaw() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "raw", enabled: isRawWanted() }));
  }
}

export function connectWs() {
  const sock = new WebSocket(wsUrl());
  ws = sock;

  sock.onopen = () => {
    useApp.getState().setConnected(true);
    sendSubscribe();
    sendRaw();
  };

  sock.onclose = () => {
    useApp.getState().setConnected(false);
    if (reconnectTimer == null) {
      reconnectTimer = window.setTimeout(() => {
        reconnectTimer = null;
        connectWs();
      }, 1000);
    }
  };

  sock.onerror = () => sock.close();

  sock.onmessage = (ev) => {
    let msg: any;
    try {
      msg = JSON.parse(ev.data);
    } catch {
      return;
    }
    const app = useApp.getState();
    switch (msg.type) {
      case "meta":
        app.setMeta(msg.signals as SignalDescriptor[], msg.pairs as Pair[]);
        app.setMotors(msg.motors as MotorView[]);
        break;
      case "motors":
        app.setMotors(msg.motors as MotorView[]);
        if (msg.status) app.setStatus(msg.status as ServerStatus);
        break;
      case "samples":
        for (const [sid, pts] of Object.entries(msg.data as Record<string, [number, number][]>)) {
          appendBatch(sid, pts);
        }
        break;
      case "raw":
        pushRawFrames(msg.frames as RawFrame[]);
        break;
    }
  };

  // re-send subscription set whenever panels change what they want (debounced)
  let subTimer: number | null = null;
  onSubscriptionsChanged(() => {
    if (subTimer != null) return;
    subTimer = window.setTimeout(() => {
      subTimer = null;
      sendSubscribe();
    }, 80);
  });
  onRawWantChanged(sendRaw);
}

export async function fetchSnapshot(ids: string[], n = 600): Promise<Record<string, [number, number][]>> {
  if (!ids.length) return {};
  const res = await fetch(`/api/monitor/snapshot?signals=${ids.join(",")}&n=${n}`);
  return res.json();
}

export async function fetchMotorTypes(): Promise<string[]> {
  try {
    const res = await fetch("/api/monitor/motor-types");
    const d = await res.json();
    return d.types || [];
  } catch {
    return [];
  }
}

export async function setMotorType(motorId: number, motorType: string) {
  await fetch("/api/monitor/motor-type", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ motorId, motorType }),
  });
}

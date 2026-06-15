/**
 * Out-of-React time-series store.
 *
 * Holds a fixed-capacity ring buffer of (t, value) per signal so that high-rate sample
 * ingestion never triggers React re-renders. Plot panels read contiguous arrays from
 * here on a requestAnimationFrame loop. Also tracks ref-counted subscriptions so the WS
 * client can stream only the signals that some panel is currently displaying.
 */

import type { RawFrame } from "./types";

const CAPACITY = 6000; // ~ up to 60 s at 100 Hz per signal

class Ring {
  t: Float64Array;
  v: Float64Array;
  len = 0;
  head = 0; // index of next write
  constructor(cap = CAPACITY) {
    this.t = new Float64Array(cap);
    this.v = new Float64Array(cap);
  }
  push(t: number, v: number) {
    const cap = this.t.length;
    this.t[this.head] = t;
    this.v[this.head] = v;
    this.head = (this.head + 1) % cap;
    if (this.len < cap) this.len++;
  }
  /** Return chronological contiguous arrays for points with t >= sinceT. */
  read(sinceT = -Infinity): { t: Float64Array; v: Float64Array } {
    const cap = this.t.length;
    const n = this.len;
    const start = (this.head - n + cap) % cap;
    const ts = new Float64Array(n);
    const vs = new Float64Array(n);
    let k = 0;
    for (let i = 0; i < n; i++) {
      const idx = (start + i) % cap;
      if (this.t[idx] >= sinceT) {
        ts[k] = this.t[idx];
        vs[k] = this.v[idx];
        k++;
      }
    }
    return { t: ts.subarray(0, k), v: vs.subarray(0, k) };
  }
  last(): number | null {
    if (this.len === 0) return null;
    const cap = this.t.length;
    return this.v[(this.head - 1 + cap) % cap];
  }
}

const rings = new Map<string, Ring>();

function ring(id: string): Ring {
  let r = rings.get(id);
  if (!r) {
    r = new Ring();
    rings.set(id, r);
  }
  return r;
}

export function appendSample(id: string, t: number, v: number) {
  ring(id).push(t, v);
}

export function appendBatch(id: string, points: [number, number][]) {
  const r = ring(id);
  for (const [t, v] of points) r.push(t, v);
}

export function readSeries(id: string, sinceT = -Infinity) {
  const r = rings.get(id);
  if (!r) return { t: new Float64Array(0), v: new Float64Array(0) };
  return r.read(sinceT);
}

export function lastValue(id: string): number | null {
  const r = rings.get(id);
  return r ? r.last() : null;
}

// ---------------------------------------------------------------- subscriptions
const subCounts = new Map<string, number>();
let subListeners: (() => void)[] = [];

function notifySubs() {
  subListeners.forEach((fn) => fn());
}

export function subscribeSignal(id: string) {
  subCounts.set(id, (subCounts.get(id) || 0) + 1);
  notifySubs();
}

export function unsubscribeSignal(id: string) {
  const c = (subCounts.get(id) || 0) - 1;
  if (c <= 0) subCounts.delete(id);
  else subCounts.set(id, c);
  notifySubs();
}

export function currentSubscriptions(): string[] {
  return Array.from(subCounts.keys());
}

export function onSubscriptionsChanged(fn: () => void): () => void {
  subListeners.push(fn);
  return () => {
    subListeners = subListeners.filter((f) => f !== fn);
  };
}

// ----------------------------------------------------------------- raw frames
const RAW_CAP = 3000;
let rawFrames: RawFrame[] = [];
let rawListeners: (() => void)[] = [];

export function pushRawFrames(frames: RawFrame[]) {
  if (!frames.length) return;
  rawFrames = rawFrames.concat(frames);
  if (rawFrames.length > RAW_CAP) rawFrames = rawFrames.slice(-RAW_CAP);
  rawListeners.forEach((fn) => fn());
}

export function getRawFrames(): RawFrame[] {
  return rawFrames;
}

export function onRawFrames(fn: () => void): () => void {
  rawListeners.push(fn);
  return () => {
    rawListeners = rawListeners.filter((f) => f !== fn);
  };
}

// raw enable ref-count (so /stream only sends raw when a RawLog panel is open)
let rawWanted = 0;
let rawWantListeners: (() => void)[] = [];
export function wantRaw(on: boolean) {
  rawWanted += on ? 1 : -1;
  if (rawWanted < 0) rawWanted = 0;
  rawWantListeners.forEach((fn) => fn());
}
export function isRawWanted(): boolean {
  return rawWanted > 0;
}
export function onRawWantChanged(fn: () => void): () => void {
  rawWantListeners.push(fn);
  return () => {
    rawWantListeners = rawWantListeners.filter((f) => f !== fn);
  };
}

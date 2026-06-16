import type { SignalDescriptor } from "./types";

// Color per physical field; cmd vs fb share a hue, distinguished by dash + brightness.
const FIELD_COLORS: Record<string, string> = {
  pos: "#58a6ff",
  vel: "#3fb950",
  torque: "#d29922",
  kp: "#bc8cff",
  kd: "#f778ba",
  vel_limit: "#56d4dd",
  torque_limit: "#e3b341",
  t_mos: "#ff7b72",
  t_rotor: "#ffa657",
  status_code: "#8b949e",
};

export function fieldColor(field: string): string {
  return FIELD_COLORS[field] || "#8b949e";
}

export function signalColor(sig: { field: string; source: string }): string {
  const base = fieldColor(sig.field);
  return sig.source === "cmd" ? lighten(base, 0.15) : base;
}

export function withAlpha(hex: string, a: number): string {
  const c = hex.replace("#", "");
  const r = parseInt(c.slice(0, 2), 16);
  const g = parseInt(c.slice(2, 4), 16);
  const b = parseInt(c.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${a})`;
}

/** Plot stroke style: actual = bold solid; command = fainter, thinner "ghost" of the same hue. */
export function seriesStyle(sig: { field: string; source: string }): { stroke: string; width: number } {
  const base = fieldColor(sig.field);
  return sig.source === "cmd"
    ? { stroke: withAlpha(base, 0.45), width: 1.25 }
    : { stroke: base, width: 1.85 };
}

export function signalLabel(sig: SignalDescriptor): string {
  return `m${sig.motorId} ${sig.source}.${sig.field}`;
}

export function shortSignal(id: string): string {
  // "bus:m1:cmd.pos" -> "m1 cmd.pos"
  const parts = id.split(":");
  if (parts.length >= 3) return `${parts[1]} ${parts[2]}`;
  return id;
}

export function isCmd(id: string): boolean {
  return id.includes(":cmd.");
}

export const FIELD_ORDER = ["pos", "vel", "torque", "kp", "kd", "t_mos", "t_rotor"];

function lighten(hex: string, amount: number): string {
  const c = hex.replace("#", "");
  const r = Math.min(255, Math.round(parseInt(c.slice(0, 2), 16) + 255 * amount));
  const g = Math.min(255, Math.round(parseInt(c.slice(2, 4), 16) + 255 * amount));
  const b = Math.min(255, Math.round(parseInt(c.slice(4, 6), 16) + 255 * amount));
  return `rgb(${r},${g},${b})`;
}

export function fmt(v: number | null | undefined, digits = 3): string {
  if (v == null || Number.isNaN(v)) return "—";
  return v.toFixed(digits);
}

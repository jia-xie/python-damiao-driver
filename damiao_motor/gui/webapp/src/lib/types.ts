export interface SignalDescriptor {
  id: string;
  bus: string;
  motorId: number;
  source: "cmd" | "fb";
  field: string;
  unit: string;
  pairKey: string;
}

export interface Pair {
  pairKey: string;
  cmd: string;
  fb: string;
}

export interface MotorView {
  bus: string;
  motorId: number;
  mode: string | null;
  status: string;
  lastT: number;
  cmd: Record<string, number>;
  fb: Record<string, number>;
}

export interface ServerStatus {
  mode: "monitor" | "control";
  connected: boolean;
  channel: string | null;
  bustype: string;
  error: string | null;
  listenOnly: boolean;
  feedbackOffset: number;
  framesSeen: number;
  decodeErrors: number;
  registryVersion: number;
  defaultMotorType: string;
  demo?: boolean;
}

export interface RawFrame {
  seq: number;
  t: number;
  arb: number;
  kind: string;
  mode: string | null;
  motorId: number;
  note: string;
  fields: Record<string, number>;
  raw: string;
}

// Panel kinds are open-ended; see panels/registry.tsx for the registered set.

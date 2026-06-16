/** REST client for the unified server (control + common endpoints). */

async function jget(url: string): Promise<any> {
  const r = await fetch(url);
  return r.json();
}
async function jpost(url: string, body?: any): Promise<any> {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  return r.json();
}
async function jput(url: string, body: any): Promise<any> {
  const r = await fetch(url, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return r.json();
}

export const api = {
  status: () => jget("/api/status"),
  setMode: (mode: "control" | "monitor") => jpost("/api/mode", { mode }),
  connect: (body: { channel: string; bustype: string; bitrate?: number | null; motor_type?: string; feedback_offset?: number }) =>
    jpost("/api/connect", body),
  disconnect: () => jpost("/api/disconnect"),

  scan: (motor_type: string) => jpost("/api/control/scan", { motor_type }),
  motors: () => jget("/api/control/motors"),
  enable: (id: number) => jpost(`/api/control/motors/${id}/enable`),
  disable: (id: number) => jpost(`/api/control/motors/${id}/disable`),
  setZero: (id: number) => jpost(`/api/control/motors/${id}/set-zero`),
  clearError: (id: number) => jpost(`/api/control/motors/${id}/clear-error`),
  storeParams: (id: number) => jpost(`/api/control/motors/${id}/store-parameters`),
  command: (id: number, body: any) => jpost(`/api/control/motors/${id}/command`, body),
  state: (id: number) => jget(`/api/control/motors/${id}/state`),
  getRegisters: (id: number) => jget(`/api/control/motors/${id}/registers`),
  setRegister: (id: number, rid: number, value: number) =>
    jput(`/api/control/motors/${id}/registers/${rid}`, { value }),
  setMotorType: (id: number, motor_type: string) =>
    jput(`/api/control/motors/${id}/motor-type`, { motor_type }),

  registerTable: () => jget("/api/register-table"),
  motorTypes: () => jget("/api/motor-types"),
  canInterfaces: (bustype: string) => jget(`/api/can-interfaces?bustype=${bustype}`),
  platform: () => jget("/api/platform"),
};

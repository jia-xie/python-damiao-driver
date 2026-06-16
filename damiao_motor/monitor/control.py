"""Active control service for the unified Control/Monitor UI.

Wraps a :class:`~damiao_motor.core.controller.DaMiaoController` and, on every command and
state read, pushes the commanded values and the motor feedback into the shared
:class:`~damiao_motor.monitor.store.SignalStore` so the same realtime plots/table/cards
visualize what *we* are driving. This is offset-agnostic (the controller routes feedback
by the logical id in ``data[0]``), unlike the passive listener used in monitor mode.

This module CAN transmit — it is only ever instantiated in Control mode.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from damiao_motor.core.controller import DaMiaoController
from damiao_motor.core.motor import MOTOR_TYPE_PRESETS, REGISTER_TABLE
from damiao_motor.monitor.decode import KIND_COMMAND, KIND_FEEDBACK, DecodedFrame
from damiao_motor.monitor.store import SignalStore

TIMEOUT_REGISTER_ID = 9
TIMEOUT_UNITS_PER_MS = 20.0


def _core_motor_type(name: str) -> str:
    """Map a (possibly extended, e.g. 'DM4310') motor-type name to a core preset name
    the DaMiaoController understands ('4310'). Falls back to '4310'."""
    if name in MOTOR_TYPE_PRESETS:
        return name
    if name.startswith("DM") and name[2:] in MOTOR_TYPE_PRESETS:
        return name[2:]
    return "4310"

# command-mode -> the cmd field names the store/plots expect (match decode.py)
_CONTROL_MODES = {"MIT", "POS_VEL", "VEL", "FORCE_POS"}


class ControlService:
    def __init__(self, store: SignalStore, raw_push=None) -> None:
        self.store = store
        self._raw_push = raw_push
        self.controller: Optional[DaMiaoController] = None
        self.channel: Optional[str] = None
        self.bustype: str = "socketcan"
        self.bitrate: Optional[int] = None
        self.connected = False
        self.error: Optional[str] = None

    # ------------------------------------------------------------- lifecycle
    def connect(self, channel: str, bustype: str = "socketcan", bitrate: Optional[int] = None) -> None:
        self.disconnect()
        self.controller = DaMiaoController(channel=channel, bustype=bustype, bitrate=bitrate)
        self.channel, self.bustype, self.bitrate = channel, bustype, bitrate
        self.connected = True
        self.error = None

    def disconnect(self) -> None:
        if self.controller is not None:
            try:
                self.controller.shutdown()
            except Exception:
                pass
        self.controller = None
        self.connected = False

    def _require(self):
        if self.controller is None:
            raise RuntimeError("Not connected")
        return self.controller

    # ---------------------------------------------------------------- scan
    def scan(self, motor_type: str, settle: float = 0.5) -> List[Dict[str, Any]]:
        c = self._require()
        core_type = _core_motor_type(motor_type)
        c.motors = {}
        c._motors_by_feedback = {}
        c.flush_bus()
        for motor_id in range(0x01, 0x11):
            try:
                m = c.add_motor(motor_id=motor_id, feedback_id=0x00, motor_type=core_type)
                m.send_cmd_mit(0.0, 0.0, 0.0, 0.0, 0.0)
            except ValueError:
                pass
            except Exception:
                pass
        found: List[Dict[str, Any]] = []
        responded = set()
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < settle:
            c.poll_feedback()
            for mid, m in c.motors.items():
                if m.state and m.state.get("can_id") is not None and mid not in responded:
                    responded.add(mid)
                    found.append({"id": mid, "arb_id": m.state.get("arbitration_id") or 0,
                                  "motor_type": m.motor_type})
                    self._push_feedback(mid, m.get_states())
            time.sleep(0.01)
        # keep only responders
        c.motors = {f["id"]: c.motors[f["id"]] for f in found}
        return found

    def motors(self) -> List[Dict[str, Any]]:
        c = self._require()
        return [{"id": mid, "motor_type": m.motor_type} for mid, m in sorted(c.motors.items())]

    # ---------------------------------------------------------- store feed
    def _push_command(self, motor_id: int, mode: str, fields: Dict[str, float]) -> None:
        fr = DecodedFrame(t=time.time(), arbitration_id=motor_id, kind=KIND_COMMAND,
                          motor_id=motor_id, raw=b"", mode=mode, fields=fields)
        self.store.ingest(fr)
        if self._raw_push:
            self._raw_push(fr)

    def _push_feedback(self, motor_id: int, state: Dict[str, Any]) -> None:
        if not state:
            return
        fields = {
            "pos": float(state.get("pos", 0.0)),
            "vel": float(state.get("vel", 0.0)),
            "torque": float(state.get("torq", 0.0)),
            "t_mos": float(state.get("t_mos", 0.0)),
            "t_rotor": float(state.get("t_rotor", 0.0)),
            "status_code": float(state.get("status_code", 0)),
        }
        fr = DecodedFrame(t=time.time(), arbitration_id=motor_id + 16, kind=KIND_FEEDBACK,
                          motor_id=motor_id, raw=b"", fields=fields,
                          note=str(state.get("status", "")))
        self.store.ingest(fr)
        if self._raw_push:
            self._raw_push(fr)

    # ------------------------------------------------------------- actions
    def enable(self, motor_id: int) -> None:
        self._require().motors[motor_id].enable()

    def disable(self, motor_id: int) -> None:
        m = self._require().motors[motor_id]
        m.set_zero_command()
        m.disable()

    def set_zero(self, motor_id: int) -> None:
        self._require().motors[motor_id].set_zero_position()

    def clear_error(self, motor_id: int) -> None:
        self._require().motors[motor_id].clear_error()

    def store_parameters(self, motor_id: int) -> None:
        self._require().motors[motor_id].store_parameters()

    def set_motor_type(self, motor_id: int, motor_type: str) -> None:
        self._require().motors[motor_id].set_motor_type(_core_motor_type(motor_type))

    def command(self, motor_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        c = self._require()
        m = c.motors[motor_id]
        mode = data.get("control_mode", "MIT")
        pos = float(data.get("target_position", 0.0))
        vel = float(data.get("target_velocity", 0.0))
        kp = float(data.get("stiffness", 0.0))
        kd = float(data.get("damping", 0.0))
        tau = float(data.get("feedforward_torque", 0.0))
        vlim = float(data.get("velocity_limit", 0.0))
        tlim = float(data.get("torque_limit_ratio", 0.0))

        if mode == "MIT":
            m.send_cmd_mit(pos, vel, kp, kd, tau)
            self._push_command(motor_id, "MIT",
                               {"pos": pos, "vel": vel, "kp": kp, "kd": kd, "torque": tau})
        elif mode == "POS_VEL":
            m.send_cmd_pos_vel(pos, vel)
            self._push_command(motor_id, "POS_VEL", {"pos": pos, "vel_limit": vel})
        elif mode == "VEL":
            m.send_cmd_vel(vel)
            self._push_command(motor_id, "VEL", {"vel": vel})
        elif mode == "FORCE_POS":
            m.send_cmd_force_pos(pos, vlim, tlim)
            self._push_command(motor_id, "FORCE_POS",
                               {"pos": pos, "vel_limit": vlim, "torque_limit_ratio": tlim})
        else:
            raise ValueError(f"Unknown control_mode: {mode}")

        c.poll_feedback()
        state = m.get_states()
        self._push_feedback(motor_id, state)
        return state

    def get_state(self, motor_id: int) -> Dict[str, Any]:
        c = self._require()
        c.poll_feedback()
        state = c.motors[motor_id].get_states()
        self._push_feedback(motor_id, state)
        return state

    # ------------------------------------------------------------ registers
    def get_registers(self, motor_id: int) -> Dict[str, Any]:
        m = self._require().motors[motor_id]
        regs = m.read_all_registers(timeout=0.05)
        clean: Dict[int, Any] = {}
        for rid, value in regs.items():
            if isinstance(value, str) and value.startswith("ERROR"):
                continue
            if rid == TIMEOUT_REGISTER_ID:
                clean[rid] = float(value) / TIMEOUT_UNITS_PER_MS
            else:
                clean[rid] = value
        return {"registers": clean, "motor_type": m.motor_type}

    def set_register(self, motor_id: int, rid: int, value: Any) -> Dict[str, Any]:
        c = self._require()
        m = c.motors[motor_id]
        updated_ids: Dict[str, int] = {}

        if rid == TIMEOUT_REGISTER_ID:
            units = int(round(float(value) * TIMEOUT_UNITS_PER_MS))
            if units < 0:
                raise ValueError("Timeout must be >= 0 ms")
            m.write_register(rid, units)
        else:
            m.write_register(rid, value)

        if rid == 7:  # MST_ID / feedback id
            new_fb = int(value)
            old_fb = m.feedback_id
            m.feedback_id = new_fb
            if old_fb in c._motors_by_feedback:
                del c._motors_by_feedback[old_fb]
            c._motors_by_feedback[new_fb] = m
            updated_ids["feedback_id"] = new_fb
        elif rid == 8:  # ESC_ID / receive (motor) id
            new_id = int(value)
            old_id = m.motor_id
            m.motor_id = new_id
            if old_id in c.motors:
                del c.motors[old_id]
            c.motors[new_id] = m
            updated_ids["motor_id"] = new_id

        if rid in (7, 8):
            try:
                m.store_parameters()
            except Exception:
                pass

        return {"updated_ids": updated_ids}

    @staticmethod
    def register_table() -> List[Dict[str, Any]]:
        return [
            {"rid": r.rid, "variable": r.variable, "description": r.description,
             "access": r.access, "range_str": r.range_str, "data_type": r.data_type}
            for r in REGISTER_TABLE.values()
        ]

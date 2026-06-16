"""In-memory store for passively-observed signals.

Ingests :class:`~damiao_motor.monitor.decode.DecodedFrame` objects and maintains:

* an auto-learned **signal registry** (one entry per motor/source/field seen),
* a fixed-size **ring buffer** of ``(t, value)`` samples per signal,
* **cmd <-> feedback pairing** so the UI can overlay commanded vs. actual.

Signal id format: ``"{bus}:m{motor_id}:{source}.{field}"`` e.g. ``"can_arm_l:m1:cmd.pos"``.
The ``pairKey`` ``"{bus}:m{motor_id}:{field}"`` links the cmd and feedback variants of the
same physical quantity.

A single writer (the listener thread) calls :meth:`ingest`; readers (HTTP/WS handlers)
call the snapshot methods. All access is guarded by one lock.
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Tuple

from damiao_motor.monitor.decode import (
    DecodedFrame,
    KIND_COMMAND,
    KIND_FEEDBACK,
)

# Per-source field whitelist -> the numeric channels worth plotting/tabulating.
_COMMAND_FIELDS = ("pos", "vel", "torque", "kp", "kd", "vel_limit", "torque_limit")
_FEEDBACK_FIELDS = ("pos", "vel", "torque", "t_mos", "t_rotor", "status_code")

_UNITS = {
    "pos": "rad",
    "vel": "rad/s",
    "torque": "Nm",
    "kp": "",
    "kd": "",
    "vel_limit": "rad/s",
    "torque_limit": "Nm",
    "t_mos": "°C",
    "t_rotor": "°C",
    "status_code": "",
}


@dataclass
class SignalDescriptor:
    """Metadata for one observable signal channel."""

    id: str
    bus: str
    motor_id: int
    source: str  # "cmd" | "fb"
    field: str
    unit: str
    pair_key: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "bus": self.bus,
            "motorId": self.motor_id,
            "source": self.source,
            "field": self.field,
            "unit": self.unit,
            "pairKey": self.pair_key,
        }


@dataclass
class _Series:
    desc: SignalDescriptor
    buf: Deque[Tuple[float, float]]
    last_value: float = 0.0
    last_t: float = 0.0
    count: int = 0


@dataclass
class MotorView:
    """Aggregated latest cmd + feedback for one motor, for the table/cards views."""

    bus: str
    motor_id: int
    cmd: Dict[str, float] = field(default_factory=dict)
    fb: Dict[str, float] = field(default_factory=dict)
    mode: Optional[str] = None
    status: str = ""
    last_t: float = 0.0


class SignalStore:
    def __init__(self, bus_name: str, maxlen: int = 6000) -> None:
        self.bus_name = bus_name
        self._maxlen = maxlen
        self._lock = threading.Lock()
        self._series: Dict[str, _Series] = {}
        self._motors: Dict[int, MotorView] = {}
        # monotonically bumped whenever the registry (set of signals) changes,
        # so clients can cheaply detect "new signals appeared".
        self.registry_version = 0

    # ------------------------------------------------------------------ ingest
    def ingest(self, frame: DecodedFrame) -> None:
        if frame.kind == KIND_COMMAND:
            source, fields = "cmd", _COMMAND_FIELDS
        elif frame.kind == KIND_FEEDBACK:
            source, fields = "fb", _FEEDBACK_FIELDS
        else:
            return  # special/register/unknown frames don't produce plottable signals

        with self._lock:
            mv = self._motors.get(frame.motor_id)
            if mv is None:
                mv = MotorView(bus=self.bus_name, motor_id=frame.motor_id)
                self._motors[frame.motor_id] = mv
            mv.last_t = frame.t
            if frame.kind == KIND_COMMAND:
                mv.mode = frame.mode
                mv.cmd = dict(frame.fields)
            else:
                mv.fb = dict(frame.fields)
                mv.status = frame.note

            for fname in fields:
                if fname not in frame.fields:
                    continue
                value = float(frame.fields[fname])
                sid = f"{self.bus_name}:m{frame.motor_id}:{source}.{fname}"
                series = self._series.get(sid)
                if series is None:
                    series = _Series(
                        desc=SignalDescriptor(
                            id=sid,
                            bus=self.bus_name,
                            motor_id=frame.motor_id,
                            source=source,
                            field=fname,
                            unit=_UNITS.get(fname, ""),
                            pair_key=f"{self.bus_name}:m{frame.motor_id}:{fname}",
                        ),
                        buf=deque(maxlen=self._maxlen),
                    )
                    self._series[sid] = series
                    self.registry_version += 1
                series.buf.append((frame.t, value))
                series.last_value = value
                series.last_t = frame.t
                series.count += 1

    # --------------------------------------------------------------- snapshots
    def list_signals(self) -> List[Dict[str, object]]:
        with self._lock:
            return [s.desc.to_dict() for s in self._series.values()]

    def pairs(self) -> List[Dict[str, object]]:
        """Return cmd/feedback pairings that share a pairKey."""
        with self._lock:
            by_pair: Dict[str, Dict[str, str]] = {}
            for s in self._series.values():
                entry = by_pair.setdefault(s.desc.pair_key, {})
                entry[s.desc.source] = s.desc.id
            return [
                {"pairKey": k, "cmd": v.get("cmd"), "fb": v.get("fb")}
                for k, v in by_pair.items()
                if "cmd" in v and "fb" in v
            ]

    def series_since(self, signal_id: str, since_t: float) -> List[Tuple[float, float]]:
        with self._lock:
            s = self._series.get(signal_id)
            if s is None:
                return []
            return [pt for pt in s.buf if pt[0] > since_t]

    def series_last_n(self, signal_id: str, n: int) -> List[Tuple[float, float]]:
        with self._lock:
            s = self._series.get(signal_id)
            if s is None:
                return []
            if n <= 0 or n >= len(s.buf):
                return list(s.buf)
            return list(s.buf)[-n:]

    def latest(self, signal_ids: List[str]) -> Dict[str, Optional[float]]:
        with self._lock:
            return {
                sid: (self._series[sid].last_value if sid in self._series else None)
                for sid in signal_ids
            }

    def motor_views(self) -> List[Dict[str, object]]:
        with self._lock:
            out = []
            for mid in sorted(self._motors):
                mv = self._motors[mid]
                out.append(
                    {
                        "bus": mv.bus,
                        "motorId": mv.motor_id,
                        "mode": mv.mode,
                        "status": mv.status,
                        "lastT": mv.last_t,
                        "cmd": mv.cmd,
                        "fb": mv.fb,
                    }
                )
            return out

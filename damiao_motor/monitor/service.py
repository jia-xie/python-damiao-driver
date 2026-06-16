"""Monitor service: wires a listen-only listener to a signal store + raw-frame log.

Owns the lifecycle of a :class:`~damiao_motor.monitor.listener.PassiveCanListener` for a
single CAN bus and exposes thread-safe snapshots for the HTTP/WS layer in
:mod:`damiao_motor.monitor.server`.
"""

from __future__ import annotations

import threading
from collections import deque
from typing import Deque, Dict, List, Optional, Tuple

from damiao_motor.monitor.decode import (
    DEFAULT_FEEDBACK_OFFSET,
    DEFAULT_MOTOR_TYPE,
    MONITOR_MOTOR_PRESETS,
    DecodedFrame,
)
from damiao_motor.monitor.listener import PassiveCanListener
from damiao_motor.monitor.store import SignalStore


def _frame_to_log(seq: int, f: DecodedFrame) -> Dict[str, object]:
    return {
        "seq": seq,
        "t": round(f.t, 6),
        "arb": f.arbitration_id,
        "kind": f.kind,
        "mode": f.mode,
        "motorId": f.motor_id,
        "note": f.note,
        "fields": {k: round(v, 4) for k, v in f.fields.items()},
        "raw": f.raw.hex(),
    }


class MonitorService:
    def __init__(
        self,
        channel: str,
        bustype: str = "socketcan",
        bitrate: Optional[int] = None,
        feedback_offset: int = DEFAULT_FEEDBACK_OFFSET,
        motor_types: Optional[Dict[int, str]] = None,
        default_motor_type: str = DEFAULT_MOTOR_TYPE,
        raw_log_size: int = 4000,
        buffer_len: int = 6000,
        demo: bool = False,
    ) -> None:
        self.channel = channel
        self.bustype = bustype
        self.bitrate = bitrate
        self.default_motor_type = default_motor_type
        self.demo = demo
        self.store = SignalStore(bus_name=channel, maxlen=buffer_len)

        self._raw_lock = threading.Lock()
        self._raw_log: Deque[Dict[str, object]] = deque(maxlen=raw_log_size)
        self._raw_seq = 0

        self.error: Optional[str] = None
        self.started = False

        self.listener = PassiveCanListener(
            channel=channel,
            bustype=bustype,
            bitrate=bitrate,
            feedback_offset=feedback_offset,
            motor_types=motor_types,
            default_motor_type=default_motor_type,
            on_frame=self._on_frame,
        )
        self._demo_source = None
        if demo:
            from damiao_motor.monitor.demo import DemoSource

            self.store.bus_name = "demo"
            self._demo_source = DemoSource(on_frame=self._on_frame, bus_name="demo")

    # ---------------------------------------------------------------- lifecycle
    def start(self) -> None:
        try:
            if self._demo_source is not None:
                self._demo_source.start()
            else:
                self.listener.start()
            self.started = True
            self.error = None
        except Exception as exc:  # surface to the UI rather than crashing the server
            self.error = str(exc)
            self.started = False

    def stop(self) -> None:
        if self._demo_source is not None:
            self._demo_source.stop()
        else:
            self.listener.stop()
        self.started = False

    # ------------------------------------------------------------------ ingest
    def _on_frame(self, frame: DecodedFrame) -> None:
        self.store.ingest(frame)
        with self._raw_lock:
            self._raw_seq += 1
            self._raw_log.append(_frame_to_log(self._raw_seq, frame))

    # --------------------------------------------------------------- accessors
    def status(self) -> Dict[str, object]:
        return {
            "channel": self.channel,
            "bustype": self.bustype,
            "bitrate": self.bitrate,
            "started": self.started,
            "error": self.error,
            "listenOnly": self.listener.listen_only_applied,
            "feedbackOffset": self.listener.feedback_offset,
            "framesSeen": self.listener.frames_seen,
            "decodeErrors": self.listener.decode_errors,
            "registryVersion": self.store.registry_version,
            "defaultMotorType": self.default_motor_type,
            "demo": self.demo,
        }

    def signals(self) -> Dict[str, object]:
        return {
            "signals": self.store.list_signals(),
            "pairs": self.store.pairs(),
            "motors": self.store.motor_views(),
            "version": self.store.registry_version,
        }

    def snapshot(
        self, signal_ids: List[str], n: int
    ) -> Dict[str, List[Tuple[float, float]]]:
        return {sid: self.store.series_last_n(sid, n) for sid in signal_ids}

    def raw_since(
        self, since_seq: int, limit: int = 500
    ) -> Tuple[int, List[Dict[str, object]]]:
        with self._raw_lock:
            if not self._raw_log:
                return since_seq, []
            items = [r for r in self._raw_log if r["seq"] > since_seq]
            if len(items) > limit:
                items = items[-limit:]
            new_seq = items[-1]["seq"] if items else since_seq
            return new_seq, items

    def set_motor_type(self, motor_id: int, motor_type: str) -> None:
        self.listener.set_motor_type(motor_id, motor_type)

    @staticmethod
    def available_motor_types() -> List[str]:
        return sorted(MONITOR_MOTOR_PRESETS.keys())

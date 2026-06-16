"""Listen-only CAN reader for passive monitoring.

:class:`PassiveCanListener` opens its **own** ``can.Bus`` and decodes every frame it
sees, without ever transmitting. It is intended to run alongside another controller that
is actively driving the motors:

* On ``socketcan`` every opened socket receives its own copy of the bus RX, so a second
  listener does not steal frames from the running controller.
* ``receive_own_messages=False`` is requested, and ``CAN_RAW_LISTEN_ONLY`` is set on the
  raw socket on a best-effort basis (python-can does not expose it) as defense-in-depth.

The hard guarantee that we never perturb the bus is *structural*: this module imports
nothing that sends and never calls ``bus.send``.
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Dict, Optional

import can

from damiao_motor.monitor.decode import (
    DEFAULT_FEEDBACK_OFFSET,
    DEFAULT_MOTOR_TYPE,
    DecodedFrame,
    decode_frame,
)

FrameCallback = Callable[[DecodedFrame], None]


def _try_set_listen_only(bus: "can.BusABC") -> bool:
    """Best-effort: put the underlying socketcan raw socket into listen-only mode.

    Returns True if the option was applied. Never raises; on any failure the listener
    still never transmits (it simply may ACK frames at the hardware level).
    """
    sock = getattr(bus, "socket", None)
    if sock is None:
        return False
    try:
        import socket as _socket

        # CAN_RAW_LISTEN_ONLY is not always present in the socket module; fall back to
        # the known constant value (6) used by the Linux SocketCAN raw protocol.
        opt = getattr(_socket, "CAN_RAW_LISTEN_ONLY", 6)
        level = getattr(_socket, "SOL_CAN_RAW", 101)
        sock.setsockopt(level, opt, 1)
        return True
    except Exception:
        return False


class PassiveCanListener:
    def __init__(
        self,
        channel: str,
        bustype: str = "socketcan",
        bitrate: Optional[int] = None,
        feedback_offset: int = DEFAULT_FEEDBACK_OFFSET,
        motor_types: Optional[Dict[int, str]] = None,
        default_motor_type: str = DEFAULT_MOTOR_TYPE,
        on_frame: Optional[FrameCallback] = None,
    ) -> None:
        self.channel = channel
        self.bustype = bustype
        self.bitrate = bitrate
        self.feedback_offset = feedback_offset
        self.motor_types = dict(motor_types or {})
        self.default_motor_type = default_motor_type
        self.on_frame = on_frame

        self.bus: Optional[can.BusABC] = None
        self.listen_only_applied = False
        self._thread: Optional[threading.Thread] = None
        self._running = False
        # diagnostics
        self.frames_seen = 0
        self.decode_errors = 0

    # ------------------------------------------------------------------- bus
    def open(self) -> None:
        bus_kwargs: Dict[str, object] = {
            "channel": self.channel,
            "interface": self.bustype,
            "receive_own_messages": False,
        }
        if self.bitrate is not None:
            bus_kwargs["bitrate"] = self.bitrate
        self.bus = can.interface.Bus(**bus_kwargs)
        self.listen_only_applied = _try_set_listen_only(self.bus)

    def start(self) -> None:
        if self._running:
            return
        if self.bus is None:
            self.open()
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, name=f"passive-listener-{self.channel}", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=0.5)
            self._thread = None
        if self.bus is not None:
            try:
                self.bus.shutdown()
            except Exception:
                pass
            self.bus = None

    def set_motor_type(self, motor_id: int, motor_type: str) -> None:
        self.motor_types[motor_id] = motor_type

    # ------------------------------------------------------------------ loop
    def _loop(self) -> None:
        assert self.bus is not None
        while self._running:
            try:
                msg = self.bus.recv(timeout=0.1)
            except Exception:
                # bus closed / transient error; brief backoff then re-check _running
                time.sleep(0.01)
                continue
            if msg is None:
                continue
            self.frames_seen += 1
            try:
                frame = decode_frame(
                    msg.arbitration_id,
                    bytes(msg.data),
                    t=msg.timestamp or time.time(),
                    motor_types=self.motor_types,
                    default_motor_type=self.default_motor_type,
                    feedback_offset=self.feedback_offset,
                )
            except Exception:
                self.decode_errors += 1
                continue
            if frame is not None and self.on_frame is not None:
                self.on_frame(frame)

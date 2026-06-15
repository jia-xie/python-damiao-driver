"""Synthetic traffic source for the passive monitor.

Generates plausible command + feedback :class:`DecodedFrame` streams for a few motors
without any CAN hardware, so the dashboard can be developed, demoed, and screenshotted
anywhere. Feedback tracks the command with a small lag and noise, as a real motor would.
"""

from __future__ import annotations

import math
import threading
import time
from typing import Callable, List

from damiao_motor.monitor.decode import (
    KIND_COMMAND,
    KIND_FEEDBACK,
    DecodedFrame,
)

FrameCallback = Callable[[DecodedFrame], None]


class DemoSource:
    def __init__(self, on_frame: FrameCallback, bus_name: str = "demo",
                 motor_ids: List[int] = (1, 2, 3), rate_hz: float = 100.0) -> None:
        self.on_frame = on_frame
        self.bus_name = bus_name
        self.motor_ids = list(motor_ids)
        self.rate_hz = rate_hz
        self._running = False
        self._thread = None
        # crude per-motor first-order lag state for feedback
        self._fb_pos = {m: 0.0 for m in self.motor_ids}

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="demo-source", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=0.5)
            self._thread = None

    def _loop(self) -> None:
        period = 1.0 / self.rate_hz
        t0 = time.time()
        while self._running:
            now = time.time()
            t = now - t0
            for i, mid in enumerate(self.motor_ids):
                phase = i * 0.7
                freq = 0.25 + 0.15 * i
                cmd_pos = 1.5 * math.sin(2 * math.pi * freq * t + phase)
                cmd_vel = 1.5 * 2 * math.pi * freq * math.cos(2 * math.pi * freq * t + phase)
                kp, kd = 60.0, 1.5
                # feedback lags the command and carries noise + load torque
                lag = 0.15
                self._fb_pos[mid] += (cmd_pos - self._fb_pos[mid]) * lag
                jitter = 0.01 * math.sin(37 * t + mid)
                fb_pos = self._fb_pos[mid] + jitter
                fb_vel = cmd_vel * 0.92 + 0.05 * math.sin(53 * t + mid)
                fb_torq = kp * (cmd_pos - fb_pos) + 0.2 * math.sin(11 * t + mid)
                t_mos = 32 + 3 * math.sin(0.1 * t + mid)
                t_rotor = 35 + 4 * math.sin(0.08 * t + mid)

                self.on_frame(DecodedFrame(
                    t=now, arbitration_id=mid, kind=KIND_COMMAND, motor_id=mid,
                    raw=b"\x00" * 8, mode="MIT",
                    fields={"pos": cmd_pos, "vel": cmd_vel, "torque": 0.0, "kp": kp, "kd": kd},
                ))
                self.on_frame(DecodedFrame(
                    t=now, arbitration_id=mid + 16, kind=KIND_FEEDBACK, motor_id=mid,
                    raw=b"\x00" * 8, note="ENABLED",
                    fields={"pos": fb_pos, "vel": fb_vel, "torque": fb_torq,
                            "t_mos": t_mos, "t_rotor": t_rotor, "status_code": 1.0},
                ))
            time.sleep(period)

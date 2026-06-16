"""Tests for the passive monitor: decode round-trips and the never-transmit guarantee."""

import struct
import time

import can
import pytest

from damiao_motor.core.motor import (
    DaMiaoMotor,
    float_to_uint,
)
from damiao_motor.monitor.decode import (
    KIND_COMMAND,
    KIND_FEEDBACK,
    KIND_SPECIAL,
    decode_frame,
    resolve_limits,
)
from damiao_motor.monitor.listener import PassiveCanListener
from damiao_motor.monitor.store import SignalStore

MOTOR_ID = 3
MOTOR_TYPE = "4310"


def _motor():
    # bus is unused by the encode_* helpers, so None is fine here.
    return DaMiaoMotor(motor_id=MOTOR_ID, feedback_id=MOTOR_ID + 16, bus=None,
                       motor_type=MOTOR_TYPE)


def _make_feedback_frame(motor_id, status, pos, vel, torq, t_mos, t_rotor, lim):
    pos_u = float_to_uint(pos, lim["p_min"], lim["p_max"], 16)
    vel_u = float_to_uint(vel, lim["v_min"], lim["v_max"], 12)
    torq_u = float_to_uint(torq, lim["t_min"], lim["t_max"], 12)
    return bytes([
        (status << 4) | (motor_id & 0x0F),
        (pos_u >> 8) & 0xFF,
        pos_u & 0xFF,
        (vel_u >> 4) & 0xFF,
        ((vel_u & 0xF) << 4) | ((torq_u >> 8) & 0xF),
        torq_u & 0xFF,
        t_mos & 0xFF,
        t_rotor & 0xFF,
    ])


# --------------------------------------------------------------------- decode
def test_mit_command_roundtrip():
    m = _motor()
    data = m.encode_cmd_msg(pos=1.25, vel=-2.0, torq=0.5, kp=40.0, kd=1.5)
    frame = decode_frame(MOTOR_ID, data, t=0.0, motor_types={MOTOR_ID: MOTOR_TYPE})
    assert frame.kind == KIND_COMMAND and frame.mode == "MIT"
    assert frame.motor_id == MOTOR_ID
    assert frame.fields["pos"] == pytest.approx(1.25, abs=1e-3)
    assert frame.fields["vel"] == pytest.approx(-2.0, abs=2e-2)
    assert frame.fields["kp"] == pytest.approx(40.0, abs=0.2)
    assert frame.fields["kd"] == pytest.approx(1.5, abs=1e-2)
    assert frame.fields["torque"] == pytest.approx(0.5, abs=1e-2)


def test_pos_vel_command_roundtrip():
    data = struct.pack("<ff", 0.75, 4.0)
    frame = decode_frame(0x100 + MOTOR_ID, data, t=0.0)
    assert frame.kind == KIND_COMMAND and frame.mode == "POS_VEL"
    assert frame.motor_id == MOTOR_ID
    assert frame.fields["pos"] == pytest.approx(0.75)
    assert frame.fields["vel_limit"] == pytest.approx(4.0)


def test_vel_command_roundtrip():
    data = struct.pack("<f", -3.5) + b"\x00" * 4
    frame = decode_frame(0x200 + MOTOR_ID, data, t=0.0)
    assert frame.kind == KIND_COMMAND and frame.mode == "VEL"
    assert frame.fields["vel"] == pytest.approx(-3.5)


def test_force_pos_command_roundtrip():
    data = struct.pack("<fHH", 1.0, 5000, 5000)  # vel 50 rad/s, ratio 0.5
    frame = decode_frame(0x300 + MOTOR_ID, data, t=0.0, motor_types={MOTOR_ID: "4340"})
    assert frame.mode == "FORCE_POS"
    assert frame.fields["vel_limit"] == pytest.approx(50.0)
    assert frame.fields["torque_limit_ratio"] == pytest.approx(0.5)
    assert frame.fields["torque_limit"] == pytest.approx(0.5 * 28, abs=1e-6)


def test_feedback_roundtrip_and_disambiguation():
    lim = resolve_limits(MOTOR_TYPE)
    data = _make_feedback_frame(MOTOR_ID, 1, 2.0, 5.0, 1.0, 35, 40, lim)
    # feedback arb = motor_id + 16 (p16)
    frame = decode_frame(MOTOR_ID + 16, data, t=0.0, motor_types={MOTOR_ID: MOTOR_TYPE})
    assert frame.kind == KIND_FEEDBACK
    assert frame.motor_id == MOTOR_ID
    assert frame.fields["pos"] == pytest.approx(2.0, abs=1e-3)
    assert frame.fields["vel"] == pytest.approx(5.0, abs=2e-2)
    assert frame.fields["torque"] == pytest.approx(1.0, abs=1e-2)
    assert frame.fields["t_mos"] == 35
    assert frame.note == "ENABLED"


def test_feedback_with_undocumented_status_still_decodes():
    """Real linearbot joints 4-7 report status nibble 3 (not in the documented set);
    such frames must still classify as feedback, not be misread as commands."""
    lim = resolve_limits(MOTOR_TYPE)
    # motor id 4 -> feedback arb 20, status nibble 3
    data = _make_feedback_frame(4, 3, 1.0, 0.0, 0.0, 30, 30, lim)
    frame = decode_frame(4 + 16, data, t=0.0, motor_types={4: MOTOR_TYPE})
    assert frame.kind == KIND_FEEDBACK
    assert frame.motor_id == 4
    assert frame.fields["pos"] == pytest.approx(1.0, abs=1e-3)
    assert "UNKNOWN" in frame.note  # status 3 surfaced as UNKNOWN(3), not dropped


def test_special_command():
    frame = decode_frame(MOTOR_ID, bytes([0xFF] * 7 + [0xFC]), t=0.0)
    assert frame.kind == KIND_SPECIAL and frame.note == "enable"


def test_mit_and_feedback_not_confused():
    """A MIT command to motor 3 (arb 3) and feedback from motor 3 (arb 19) classify distinctly."""
    m = _motor()
    cmd = decode_frame(MOTOR_ID, m.encode_cmd_msg(0.0, 0.0, 0.0, 10.0, 1.0), t=0.0,
                       motor_types={MOTOR_ID: MOTOR_TYPE})
    lim = resolve_limits(MOTOR_TYPE)
    fb = decode_frame(MOTOR_ID + 16,
                      _make_feedback_frame(MOTOR_ID, 1, 0.0, 0.0, 0.0, 30, 30, lim),
                      t=0.0, motor_types={MOTOR_ID: MOTOR_TYPE})
    assert cmd.kind == KIND_COMMAND and cmd.mode == "MIT"
    assert fb.kind == KIND_FEEDBACK


# ---------------------------------------------------------------------- store
def test_store_ingest_and_pairing():
    store = SignalStore("can_test")
    m = _motor()
    lim = resolve_limits(MOTOR_TYPE)
    cmd = decode_frame(MOTOR_ID, m.encode_cmd_msg(1.0, 0.0, 0.0, 10.0, 1.0), t=1.0,
                       motor_types={MOTOR_ID: MOTOR_TYPE})
    fb = decode_frame(MOTOR_ID + 16,
                      _make_feedback_frame(MOTOR_ID, 1, 0.9, 0.0, 0.0, 30, 30, lim),
                      t=1.0, motor_types={MOTOR_ID: MOTOR_TYPE})
    store.ingest(cmd)
    store.ingest(fb)

    ids = {s["id"] for s in store.list_signals()}
    assert "can_test:m3:cmd.pos" in ids
    assert "can_test:m3:fb.pos" in ids

    pairs = store.pairs()
    pos_pair = next(p for p in pairs if p["pairKey"] == "can_test:m3:pos")
    assert pos_pair["cmd"] == "can_test:m3:cmd.pos"
    assert pos_pair["fb"] == "can_test:m3:fb.pos"

    views = store.motor_views()
    assert views[0]["motorId"] == MOTOR_ID
    assert views[0]["cmd"]["pos"] == pytest.approx(1.0, abs=1e-3)


# ------------------------------------------------------------------- listener
class _FakeBus:
    """Minimal can.Bus stand-in that records any send attempt (there must be none)."""

    def __init__(self, messages):
        self._messages = list(messages)
        self.send_called = False
        self.socket = None

    def recv(self, timeout=0.0):
        if self._messages:
            return self._messages.pop(0)
        time.sleep(0.005)
        return None

    def send(self, *a, **k):  # pragma: no cover - must never be hit
        self.send_called = True
        raise AssertionError("PassiveCanListener must never transmit")

    def shutdown(self):
        pass


def test_listener_never_transmits_and_decodes():
    lim = resolve_limits(MOTOR_TYPE)
    msgs = [
        can.Message(arbitration_id=MOTOR_ID + 16,
                    data=_make_feedback_frame(MOTOR_ID, 1, 1.0, 2.0, 0.5, 30, 31, lim),
                    timestamp=1.0, is_extended_id=False),
    ]
    received = []
    listener = PassiveCanListener(channel="vcan_test", on_frame=received.append)
    listener.bus = _FakeBus(msgs)  # inject; start() won't re-open since bus is set
    listener.start()
    deadline = time.time() + 1.0
    while not received and time.time() < deadline:
        time.sleep(0.01)
    listener.stop()

    assert received, "listener should have decoded the injected feedback frame"
    assert received[0].kind == KIND_FEEDBACK
    assert received[0].motor_id == MOTOR_ID


def test_listener_source_has_no_send_call():
    """Belt-and-suspenders: the listener module never references bus.send."""
    import damiao_motor.monitor.listener as lst

    with open(lst.__file__) as f:
        src = f.read()
    assert ".send(" not in src

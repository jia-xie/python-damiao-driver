"""Passive decode of DaMiao CAN frames — both commands and feedback.

This module reverses the frame encoders in :mod:`damiao_motor.core.motor` so that a
listen-only observer can reconstruct what *another* controller is commanding on the
bus, alongside the motors' feedback. It never transmits anything.

Frame layouts (little detail recap, see core/motor.py for the encoders):

* MIT command         arb = motor_id            16b pos | 12b vel | 12b kp | 12b kd | 12b torque
* POS_VEL command     arb = 0x100 + motor_id    <ff>  (target_pos, vel_limit)
* VEL command         arb = 0x200 + motor_id    <f>   (target_vel) + 4 pad
* FORCE_POS command   arb = 0x300 + motor_id    <fHH> (pos, vel*100, ratio*10000)
* special command     arb = motor_id            FF*7 + {FC enable, FD disable, FE zero, FB clear}
* feedback            arb = motor_id + offset   D0=(status<<4)|can_id, packed pos/vel/torque, D6/D7 temps
* register reply      D1<=0x0F, D2==0x33, D3=rid

Command and feedback share the low arbitration-id space, so they are disambiguated by
the feedback-id ``offset`` (e.g. the I2RT ``p16`` scheme uses ``motor_id + 16``) together
with the structural check ``data[0] & 0x0F == arb - offset``.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Dict, Optional

from damiao_motor.core.motor import (
    KD_MAX,
    KD_MIN,
    KP_MAX,
    KP_MIN,
    MOTOR_TYPE_PRESETS,
    _STATE_NAME_MAP,
    _decode_status_name,
    is_register_reply,
    uint_to_float,
)

# Arbitration-id bases for the non-MIT control modes.
POS_VEL_BASE = 0x100
VEL_BASE = 0x200
FORCE_POS_BASE = 0x300
REGISTER_ARB = 0x7FF

# Default feedback-id offset: the I2RT "p16" receive mode (feedback arb = motor_id + 16),
# which is also the common DaMiao default. Configurable per listener.
DEFAULT_FEEDBACK_OFFSET = 16

# Valid DM status nibbles (used as a structural gate when classifying feedback frames).
KNOWN_STATUS = frozenset(_STATE_NAME_MAP.keys())

# Special single-byte command suffixes (data = FF*7 + suffix).
_SPECIAL_SUFFIX = {
    0xFC: "enable",
    0xFD: "disable",
    0xFE: "set_zero",
    0xFB: "clear_error",
}

# Extended motor-type presets. We reuse the core presets (keyed "4310", "4340", ...) and
# add the "DM"-prefixed names plus the reduced-range variants used by third-party stacks
# (e.g. DM4310V / DM_FLOW_WHEEL use +/-pi rad position), so we can decode their traffic
# correctly without touching the core table.
_EXTRA_LIMIT_PARAM = {
    # name: (pmax, vmax, tmax)  -> symmetric +/- ranges
    "DM4310": (12.5, 30, 10),
    "DM4310V": (3.1415926, 30, 10),
    "DM_FLOW_WHEEL": (3.1415926, 30, 10),
    "DMH6215": (3.1415926, 30, 10),
    "DMH6215MIT": (12.5, 45, 10),
    "DM4340": (12.5, 10, 28),
    "DM6248": (12.5, 20, 120),
    "DM8009": (12.5, 45, 54),
    "DM3507": (12.5, 50, 5),
}


def _preset_from_param(pmax: float, vmax: float, tmax: float) -> Dict[str, float]:
    return {
        "p_min": -pmax,
        "p_max": pmax,
        "v_min": -vmax,
        "v_max": vmax,
        "t_min": -tmax,
        "t_max": tmax,
    }


# Merged lookup: core presets first, then the extended/DM-prefixed names.
MONITOR_MOTOR_PRESETS: Dict[str, Dict[str, float]] = {
    **MOTOR_TYPE_PRESETS,
    **{name: _preset_from_param(*p) for name, p in _EXTRA_LIMIT_PARAM.items()},
}

DEFAULT_MOTOR_TYPE = "DM4310"


def resolve_limits(motor_type: str) -> Dict[str, float]:
    """Resolve P/V/T limits for a motor type, tolerant of the ``DM`` name prefix.

    Falls back to :data:`DEFAULT_MOTOR_TYPE` for unknown names so a single unexpected
    motor never breaks passive decoding of the rest of the bus.
    """
    if motor_type in MONITOR_MOTOR_PRESETS:
        return MONITOR_MOTOR_PRESETS[motor_type]
    # tolerate "DM4310" <-> "4310"
    alt = motor_type[2:] if motor_type.startswith("DM") else f"DM{motor_type}"
    if alt in MONITOR_MOTOR_PRESETS:
        return MONITOR_MOTOR_PRESETS[alt]
    return MONITOR_MOTOR_PRESETS[DEFAULT_MOTOR_TYPE]


# Frame kinds.
KIND_COMMAND = "command"
KIND_FEEDBACK = "feedback"
KIND_SPECIAL = "special"
KIND_REGISTER = "register"
KIND_UNKNOWN = "unknown"


@dataclass
class DecodedFrame:
    """A single passively-decoded CAN frame."""

    t: float
    arbitration_id: int
    kind: str
    motor_id: int
    raw: bytes
    mode: Optional[str] = None  # MIT / POS_VEL / VEL / FORCE_POS for commands
    fields: Dict[str, float] = field(default_factory=dict)
    note: str = ""


def _u16_be(data: bytes, i: int) -> int:
    return (data[i] << 8) | data[i + 1]


def _decode_mit(data: bytes, lim: Dict[str, float]) -> Dict[str, float]:
    pos_u = (data[0] << 8) | data[1]
    vel_u = (data[2] << 4) | (data[3] >> 4)
    kp_u = ((data[3] & 0xF) << 8) | data[4]
    kd_u = (data[5] << 4) | (data[6] >> 4)
    torq_u = ((data[6] & 0xF) << 8) | data[7]
    return {
        "pos": uint_to_float(pos_u, lim["p_min"], lim["p_max"], 16),
        "vel": uint_to_float(vel_u, lim["v_min"], lim["v_max"], 12),
        "kp": uint_to_float(kp_u, KP_MIN, KP_MAX, 12),
        "kd": uint_to_float(kd_u, KD_MIN, KD_MAX, 12),
        "torque": uint_to_float(torq_u, lim["t_min"], lim["t_max"], 12),
    }


def _decode_feedback(data: bytes, lim: Dict[str, float]) -> Dict[str, float]:
    status = data[0] >> 4
    pos_int = (data[1] << 8) | data[2]
    vel_int = (data[3] << 4) | (data[4] >> 4)
    torq_int = ((data[4] & 0xF) << 8) | data[5]
    return {
        "status_code": float(status),
        "pos": uint_to_float(pos_int, lim["p_min"], lim["p_max"], 16),
        "vel": uint_to_float(vel_int, lim["v_min"], lim["v_max"], 12),
        "torque": uint_to_float(torq_int, lim["t_min"], lim["t_max"], 12),
        "t_mos": float(data[6]),
        "t_rotor": float(data[7]),
    }


def _looks_like_feedback(arb: int, data: bytes, offset: int) -> Optional[int]:
    """Return the motor id if the frame looks like a feedback frame, else None."""
    mid = arb - offset
    if 1 <= mid <= 15 and (data[0] & 0x0F) == mid and (data[0] >> 4) in KNOWN_STATUS:
        return mid
    return None


def decode_frame(
    arbitration_id: int,
    data: bytes,
    t: float,
    motor_types: Optional[Dict[int, str]] = None,
    default_motor_type: str = DEFAULT_MOTOR_TYPE,
    feedback_offset: int = DEFAULT_FEEDBACK_OFFSET,
) -> Optional[DecodedFrame]:
    """Classify and decode one observed CAN frame.

    Args:
        arbitration_id: 11-bit CAN id.
        data: frame payload (must be 8 bytes to decode motor frames).
        t: observation timestamp (seconds).
        motor_types: optional per-motor-id motor type used to scale pos/vel/torque.
        default_motor_type: fallback motor type when an id is not in ``motor_types``.
        feedback_offset: feedback arb = motor_id + offset (16 for the I2RT p16 scheme).

    Returns:
        A :class:`DecodedFrame`, or ``None`` if the frame can't be interpreted.
    """
    motor_types = motor_types or {}
    if len(data) != 8:
        return None

    def lim_for(mid: int) -> Dict[str, float]:
        return resolve_limits(motor_types.get(mid, default_motor_type))

    # 1) Register reply (motor -> bus). Structural test, arb-independent.
    if is_register_reply(data):
        motor_id = data[0] | (data[1] << 8)
        return DecodedFrame(
            t=t,
            arbitration_id=arbitration_id,
            kind=KIND_REGISTER,
            motor_id=motor_id,
            raw=bytes(data),
            fields={"rid": float(data[3])},
            note="register reply",
        )

    # 2) Special commands (FF*7 + suffix).
    if data[:7] == b"\xff\xff\xff\xff\xff\xff\xff" and data[7] in _SPECIAL_SUFFIX:
        return DecodedFrame(
            t=t,
            arbitration_id=arbitration_id,
            kind=KIND_SPECIAL,
            motor_id=arbitration_id,
            raw=bytes(data),
            note=_SPECIAL_SUFFIX[data[7]],
        )

    # 3) Non-MIT command modes by arbitration-id window.
    if POS_VEL_BASE <= arbitration_id < POS_VEL_BASE + 0x100:
        mid = arbitration_id - POS_VEL_BASE
        pos, vel_limit = struct.unpack("<ff", data[:8])
        return DecodedFrame(t, arbitration_id, KIND_COMMAND, mid, bytes(data),
                            mode="POS_VEL", fields={"pos": pos, "vel_limit": vel_limit})
    if VEL_BASE <= arbitration_id < VEL_BASE + 0x100:
        mid = arbitration_id - VEL_BASE
        (vel,) = struct.unpack("<f", data[:4])
        return DecodedFrame(t, arbitration_id, KIND_COMMAND, mid, bytes(data),
                            mode="VEL", fields={"vel": vel})
    if FORCE_POS_BASE <= arbitration_id < FORCE_POS_BASE + 0x100:
        mid = arbitration_id - FORCE_POS_BASE
        pos, v_scaled, i_scaled = struct.unpack("<fHH", data[:8])
        lim = lim_for(mid)
        return DecodedFrame(
            t, arbitration_id, KIND_COMMAND, mid, bytes(data),
            mode="FORCE_POS",
            fields={
                "pos": pos,
                "vel_limit": v_scaled / 100.0,
                "torque_limit_ratio": i_scaled / 10000.0,
                "torque_limit": (i_scaled / 10000.0) * lim["t_max"],
            },
        )

    # 4) Feedback (motor -> bus), via offset + structural check.
    mid = _looks_like_feedback(arbitration_id, data, feedback_offset)
    if mid is not None:
        lim = lim_for(mid)
        fb = _decode_feedback(data, lim)
        status_name = _decode_status_name(int(fb["status_code"]))
        return DecodedFrame(t, arbitration_id, KIND_FEEDBACK, mid, bytes(data),
                            fields=fb, note=status_name)

    # 5) Otherwise treat a low-id frame as an MIT command.
    if 1 <= arbitration_id < POS_VEL_BASE:
        lim = lim_for(arbitration_id)
        return DecodedFrame(t, arbitration_id, KIND_COMMAND, arbitration_id, bytes(data),
                            mode="MIT", fields=_decode_mit(data, lim))

    # 6) Register command space / anything else.
    if arbitration_id == REGISTER_ARB:
        return DecodedFrame(t, arbitration_id, KIND_REGISTER,
                            data[0] | (data[1] << 8), bytes(data), note="register cmd")

    return DecodedFrame(t, arbitration_id, KIND_UNKNOWN, arbitration_id, bytes(data))

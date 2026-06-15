"""Passive (listen-only) monitoring for DaMiao motors.

This subpackage decodes both command and feedback frames observed on a CAN bus while
another controller drives the motors, and never transmits anything itself.
"""

from damiao_motor.monitor.decode import DecodedFrame, decode_frame, resolve_limits
from damiao_motor.monitor.listener import PassiveCanListener
from damiao_motor.monitor.store import SignalDescriptor, SignalStore

__all__ = [
    "DecodedFrame",
    "decode_frame",
    "resolve_limits",
    "PassiveCanListener",
    "SignalStore",
    "SignalDescriptor",
]

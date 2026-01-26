"""Core motor and controller functionality."""
from .motor import (
    DaMiaoMotor,
    REGISTER_TABLE,
    RegisterInfo,
    CAN_BAUD_RATE_CODES,
    MOTOR_TYPE_PRESETS,
    KP_MIN,
    KP_MAX,
    KD_MIN,
    KD_MAX,
)
from .controller import DaMiaoController

__all__ = [
    "DaMiaoMotor",
    "DaMiaoController",
    "REGISTER_TABLE",
    "RegisterInfo",
    "CAN_BAUD_RATE_CODES",
    "MOTOR_TYPE_PRESETS",
    "KP_MIN",
    "KP_MAX",
    "KD_MIN",
    "KD_MAX",
]

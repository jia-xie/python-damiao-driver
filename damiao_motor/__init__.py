# Re-export from core for backward compatibility
from .core import (
    DaMiaoMotor,
    DaMiaoController,
    REGISTER_TABLE,
    RegisterInfo,
    CAN_BAUD_RATE_CODES,
    MOTOR_TYPE_PRESETS,
    KP_MIN,
    KP_MAX,
    KD_MIN,
    KD_MAX,
)

try:
    from ._version import version as __version__  # type: ignore
except ImportError:
    try:
        from importlib.metadata import version as _version
        __version__ = _version("damiao-motor")
    except Exception:
        try:
            from setuptools_scm import get_version  # type: ignore
            __version__ = get_version(root="..", relative_to=__file__)
        except Exception:
            __version__ = "unknown"

__all__ = ["DaMiaoMotor", "DaMiaoController", "REGISTER_TABLE", "RegisterInfo", "CAN_BAUD_RATE_CODES", "MOTOR_TYPE_PRESETS", "KP_MIN", "KP_MAX", "KD_MIN", "KD_MAX", "__version__"]



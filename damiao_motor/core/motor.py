import can
import struct
import time
from typing import Dict, Any, List, Optional, Tuple, Literal
from dataclasses import dataclass
import threading

# -----------------------
# Register table
# -----------------------

@dataclass
class RegisterInfo:
    """Information about a motor register."""
    rid: int
    variable: str
    description: str
    access: Literal["RW", "RO"]
    range_str: str
    data_type: Literal["float", "uint32"]

# Register table based on manufacturer documentation
REGISTER_TABLE: Dict[int, RegisterInfo] = {
    # Protection and basic parameters (0-6)
    0: RegisterInfo(0, "UV_Value", "Under-voltage protection value", "RW", "(10.0, 3.4E38]", "float"),
    1: RegisterInfo(1, "KT_Value", "Torque coefficient", "RW", "[0.0, 3.4E38]", "float"),
    2: RegisterInfo(2, "OT_Value", "Over-temperature protection value", "RW", "[80.0, 200)", "float"),
    3: RegisterInfo(3, "OC_Value", "Over-current protection value", "RW", "(0.0, 1.0)", "float"),
    4: RegisterInfo(4, "ACC", "Acceleration", "RW", "(0.0, 3.4E38)", "float"),
    5: RegisterInfo(5, "DEC", "Deceleration", "RW", "[-3.4E38, 0.0)", "float"),
    6: RegisterInfo(6, "MAX_SPD", "Maximum speed", "RW", "(0.0, 3.4E38]", "float"),
    
    # System identification and configuration (7-10)
    7: RegisterInfo(7, "MST_ID", "Feedback ID", "RW", "[0, 0x7FF]", "uint32"),
    8: RegisterInfo(8, "ESC_ID", "Receive ID", "RW", "[0, 0x7FF]", "uint32"),
    9: RegisterInfo(9, "TIMEOUT", "Timeout alarm time (1 unit = 50 microseconds)", "RW", "[0, 2^32-1]", "uint32"),
    10: RegisterInfo(10, "CTRL_MODE", "Control mode", "RW", "[1, 4]", "uint32"),
    
    # Motor physical parameters (11-20) - Read Only
    11: RegisterInfo(11, "Damp", "Motor viscous damping coefficient", "RO", "/", "float"),
    12: RegisterInfo(12, "Inertia", "Motor moment of inertia", "RO", "/", "float"),
    13: RegisterInfo(13, "hw_ver", "Reserved", "RO", "/", "uint32"),
    14: RegisterInfo(14, "sw_ver", "Software version number", "RO", "/", "uint32"),
    15: RegisterInfo(15, "SN", "Reserved", "RO", "/", "uint32"),
    16: RegisterInfo(16, "NPP", "Motor pole pairs", "RO", "/", "uint32"),
    17: RegisterInfo(17, "Rs", "Motor phase resistance", "RO", "/", "float"),
    18: RegisterInfo(18, "Ls", "Motor phase inductance", "RO", "/", "float"),
    19: RegisterInfo(19, "Flux", "Motor flux linkage value", "RO", "/", "float"),
    20: RegisterInfo(20, "Gr", "Gear reduction ratio", "RO", "/", "float"),
    
    # Mapping ranges (21-23)
    21: RegisterInfo(21, "PMAX", "Position mapping range", "RW", "(0.0, 3.4E38]", "float"),
    22: RegisterInfo(22, "VMAX", "Speed mapping range", "RW", "(0.0, 3.4E38]", "float"),
    23: RegisterInfo(23, "TMAX", "Torque mapping range", "RW", "(0.0, 3.4E38]", "float"),
    
    # Control loop parameters (24-28)
    24: RegisterInfo(24, "I_BW", "Current loop control bandwidth", "RW", "[100.0, 10000.0]", "float"),
    25: RegisterInfo(25, "KP_ASR", "Speed loop Kp", "RW", "[0.0, 3.4E38]", "float"),
    26: RegisterInfo(26, "KI_ASR", "Speed loop Ki", "RW", "[0.0, 3.4E38]", "float"),
    27: RegisterInfo(27, "KP_APR", "Position loop Kp", "RW", "[0.0, 3.4E38]", "float"),
    28: RegisterInfo(28, "KI_APR", "Position loop Ki", "RW", "[0.0, 3.4E38]", "float"),
    
    # Protection and efficiency (29-32)
    29: RegisterInfo(29, "OV_Value", "Overvoltage protection value", "RW", "TBD", "float"),
    30: RegisterInfo(30, "GREF", "Gear torque efficiency", "RW", "(0.0, 1.0]", "float"),
    31: RegisterInfo(31, "Deta", "Speed loop damping coefficient", "RW", "[1.0, 30.0]", "float"),
    32: RegisterInfo(32, "V_BW", "Speed loop filter bandwidth", "RW", "(0.0, 500.0)", "float"),
    
    # Enhancement coefficients (33-34)
    33: RegisterInfo(33, "IQ_c1", "Current loop enhancement coefficient", "RW", "[100.0, 10000.0]", "float"),
    34: RegisterInfo(34, "VL_c1", "Speed loop enhancement coefficient", "RW", "(0.0, 10000.0]", "float"),
    
    # CAN and version (35-36)
    35: RegisterInfo(35, "can_br", "CAN baud rate code", "RW", "[0, 4]", "uint32"),
    36: RegisterInfo(36, "sub_ver", "Sub-version number", "RO", "/", "uint32"),
    
    # Calibration parameters (50-55) - Read Only
    50: RegisterInfo(50, "u_off", "U-phase offset", "RO", "", "float"),
    51: RegisterInfo(51, "v_off", "V-phase offset", "RO", "", "float"),
    52: RegisterInfo(52, "k1", "Compensation factor 1", "RO", "", "float"),
    53: RegisterInfo(53, "k2", "Compensation factor 2", "RO", "", "float"),
    54: RegisterInfo(54, "m_off", "Angle offset", "RO", "", "float"),
    55: RegisterInfo(55, "dir", "Direction", "RO", "", "float"),
    
    # Motor and driver board parameters (56, 59-65) - Read Only
    56: RegisterInfo(56, "m_off", "Motor side angle offset", "RO", "", "float"),
    59: RegisterInfo(59, "Imax", "Driver board maximum current", "RO", "", "float"),
    60: RegisterInfo(60, "VBus", "Power supply voltage", "RO", "", "float"),
    61: RegisterInfo(61, "Tpcb", "Driver board temperature", "RO", "", "float"),
    62: RegisterInfo(62, "Tmtr", "Motor temperature", "RO", "", "float"),
    63: RegisterInfo(63, "Iu_off", "U-phase current offset", "RO", "", "float"),
    64: RegisterInfo(64, "Iv_off", "V-phase current offset", "RO", "", "float"),
    65: RegisterInfo(65, "Iw_off", "W-phase current offset", "RO", "", "float"),
    
    # Position feedback (80-81) - Read Only
    80: RegisterInfo(80, "p_m", "Motor position", "RO", "", "float"),
    81: RegisterInfo(81, "xout", "Output shaft position", "RO", "", "float"),
}

# CAN baud rate codes
CAN_BAUD_RATE_CODES = {
    0: 125000,   # 125K
    1: 200000,   # 200K
    2: 250000,   # 250K
    3: 500000,   # 500K
    4: 1000000,  # 1M
}

# -----------------------
# Helper functions
# -----------------------
def is_register_reply(data: bytes) -> bool:
    """
    Check if a CAN frame is a register reply frame.
    
    Conditions:
    - D[1] is 0x00-0x0F (0-15)
    - D[2] is 0x33
    - D[3] is a valid register number (0-81)
    
    Args:
        data: 8-byte CAN frame data
        
    Returns:
        True if this appears to be a register reply frame
    """
    if len(data) < 4:
        return False
    
    # D[1] should be 0x00-0x0F
    if data[1] > 0x0F:
        return False
    
    # D[2] should be 0x33
    if data[2] != 0x33:
        return False
    
    # D[3] should be a valid register number (0-81)
    rid = data[3]
    if rid not in REGISTER_TABLE:
        return False
    
    return True

# -----------------------
# Motor parameter limits and presets
# -----------------------
# P/V/T min/max per motor type: [PMAX, VMAX, TMAX] -> p=±PMAX, v=±VMAX, t=±TMAX.
# kp_min/kp_max and kd_min/kd_max are fixed for all motors (MIT mode stiffness/damping encoding).
KP_MIN = 0.0
KP_MAX = 500.0
KD_MIN = 0.0
KD_MAX = 5.0

# [PMAX, VMAX, TMAX] per motor type (Limit_Param table)
_MOTOR_LIMIT_PARAM: List[Tuple[str, List[float]]] = [
    ("4310", [12.5, 30, 10]),
    ("4310P", [12.5, 50, 10]),
    ("4340", [12.5, 10, 28]),
    ("4340P", [12.5, 10, 28]),
    ("6006", [12.5, 45, 20]),
    ("8006", [12.5, 45, 40]),
    ("8009", [12.5, 45, 54]),
    ("10010L", [12.5, 25, 200]),
    ("10010", [12.5, 20, 200]),
    ("H3510", [12.5, 280, 1]),
    ("G6215", [12.5, 45, 10]),
    ("H6220", [12.5, 45, 10]),
    ("JH11", [12.5, 10, 12]),
    ("6248P", [12.566, 20, 120]),
    ("3507", [12.566, 50, 5]),
]

def _build_preset(pmax: float, vmax: float, tmax: float) -> Dict[str, float]:
    return {
        "p_min": -pmax, "p_max": pmax,
        "v_min": -vmax, "v_max": vmax,
        "t_min": -tmax, "t_max": tmax,
    }

MOTOR_TYPE_PRESETS: Dict[str, Dict[str, float]] = {
    name: _build_preset(p, v, t) for name, (p, v, t) in _MOTOR_LIMIT_PARAM
}

_LIMITS_KEYS = ("p_min", "p_max", "v_min", "v_max", "t_min", "t_max")

# -----------------------
# Motor state codes
# -----------------------
DM_MOTOR_DISABLED = 0x0
DM_MOTOR_ENABLED = 0x1
DM_MOTOR_OVER_VOLTAGE = 0x8
DM_MOTOR_UNDER_VOLTAGE = 0x9
DM_MOTOR_OVER_CURRENT = 0xA
DM_MOTOR_MOS_OVER_TEMP = 0xB
DM_MOTOR_ROTOR_OVER_TEMP = 0xC
DM_MOTOR_LOST_COMM = 0xD
DM_MOTOR_OVERLOAD = 0xE

_STATE_NAME_MAP = {
    DM_MOTOR_DISABLED: "DISABLED",
    DM_MOTOR_ENABLED: "ENABLED",
    DM_MOTOR_OVER_VOLTAGE: "OVER_VOLTAGE",
    DM_MOTOR_UNDER_VOLTAGE: "UNDER_VOLTAGE",
    DM_MOTOR_OVER_CURRENT: "OVER_CURRENT",
    DM_MOTOR_MOS_OVER_TEMP: "MOS_OVER_TEMP",
    DM_MOTOR_ROTOR_OVER_TEMP: "ROTOR_OVER_TEMP",
    DM_MOTOR_LOST_COMM: "LOST_COMM",
    DM_MOTOR_OVERLOAD: "OVERLOAD",
}


def decode_state_name(state_code: int) -> str:
    """Return human-readable name for a motor state code."""
    return _STATE_NAME_MAP.get(state_code, f"UNKNOWN({state_code})")


def float_to_uint(x: float, x_min: float, x_max: float, bits: int) -> int:
    span = x_max - x_min
    x_clipped = min(max(x, x_min), x_max)
    return int((x_clipped - x_min) * ((1 << bits) - 1) / span)


def uint_to_float(x_int: int, x_min: float, x_max: float, bits: int) -> float:
    span = x_max - x_min
    return float(x_int) * span / ((1 << bits) - 1) + x_min


class DaMiaoMotor:
    """
    Lightweight DaMiao motor wrapper over a CAN bus.
    """

    def __init__(
        self,
        motor_id: int,
        feedback_id: int,
        bus: can.Bus,
        *,
        motor_type: str,
        p_min: Optional[float] = None,
        p_max: Optional[float] = None,
        v_min: Optional[float] = None,
        v_max: Optional[float] = None,
        t_min: Optional[float] = None,
        t_max: Optional[float] = None,
    ) -> None:
        self.motor_id = motor_id
        self.feedback_id = feedback_id
        self.bus = bus

        # Resolve P/V/T limits from motor_type preset + optional overrides. kp and kd use fixed KP_MIN/KP_MAX, KD_MIN/KD_MAX.
        base = self._resolve_limits(motor_type)
        overrides = {
            k: v
            for k, v in (
                ("p_min", p_min), ("p_max", p_max),
                ("v_min", v_min), ("v_max", v_max),
                ("t_min", t_min), ("t_max", t_max),
            )
            if v is not None
        }
        base.update(overrides)
        for k in _LIMITS_KEYS:
            setattr(self, f"_{k}", base[k])

        self.motor_type = motor_type

        # last decoded feedback
        self.state: Dict[str, Any] = {}
        self.state_lock = threading.Lock()

        # last register values
        self.registers: Dict[int, float | int] = {}
        self.registers_lock = threading.Lock()
        self.register_request_time: Dict[int, float] = {}
        self.register_request_time_lock = threading.Lock()
        self.register_reply_time: Dict[int, float] = {}
        self.register_reply_time_lock = threading.Lock()

    def _resolve_limits(self, motor_type: str) -> Dict[str, float]:
        """Resolve limits from motor_type preset. Returns a dict of the 6 P/V/T limit values."""
        if motor_type not in MOTOR_TYPE_PRESETS:
            raise ValueError(
                f"Unknown motor_type: {motor_type!r}. "
                f"Known: {list(MOTOR_TYPE_PRESETS.keys())}"
            )
        return dict(MOTOR_TYPE_PRESETS[motor_type])

    def set_motor_type(self, motor_type: str) -> None:
        """Update motor type and P/V/T limits from a preset. Validates against MOTOR_TYPE_PRESETS."""
        if motor_type not in MOTOR_TYPE_PRESETS:
            raise ValueError(
                f"Unknown motor_type: {motor_type!r}. "
                f"Known: {list(MOTOR_TYPE_PRESETS.keys())}"
            )
        base = dict(MOTOR_TYPE_PRESETS[motor_type])
        for k in _LIMITS_KEYS:
            setattr(self, f"_{k}", base[k])
        self.motor_type = motor_type

    def get_states(self) -> Dict[str, Any]:
        """
        Get the current motor state dictionary.
        
        Returns:
            Dictionary containing current motor state information:
            - can_id: CAN ID
            - status: Human-readable status name
            - status_code: Status code
            - pos: Position
            - vel: Velocity
            - torq: Torque
            - t_mos: MOSFET temperature
            - t_rotor: Rotor temperature
            - arbitration_id: CAN arbitration ID
        """
        return self.state.copy() if self.state else {}

    # -----------------------
    # Encode messages
    # -----------------------
    def encode_cmd_msg(self, pos: float, vel: float, torq: float, kp: float, kd: float) -> bytes:
        """
        Encode a command to CAN frame for sending to the motor.
        Uses this motor's P/V/T limits (from motor_type preset) and fixed kp (KP_MIN/KP_MAX), kd (KD_MIN/KD_MAX).
        """
        pos_u = float_to_uint(pos, self._p_min, self._p_max, 16)
        vel_u = float_to_uint(vel, self._v_min, self._v_max, 12)
        kp_u = float_to_uint(kp, KP_MIN, KP_MAX, 12)
        kd_u = float_to_uint(kd, KD_MIN, KD_MAX, 12)
        torq_u = float_to_uint(torq, self._t_min, self._t_max, 12)

        data = [
            (pos_u >> 8) & 0xFF,
            pos_u & 0xFF,
            (vel_u >> 4) & 0xFF,
            ((vel_u & 0xF) << 4) | ((kp_u >> 8) & 0xF),
            kp_u & 0xFF,
            (kd_u >> 4) & 0xFF,
            ((kd_u & 0xF) << 4) | ((torq_u >> 8) & 0xF),
            torq_u & 0xFF,
        ]
        return bytes(data)

    @staticmethod
    def encode_enable_msg() -> bytes:
        return bytes([0xFF] * 7 + [0xFC])

    @staticmethod
    def encode_disable_msg() -> bytes:
        return bytes([0xFF] * 7 + [0xFD])

    @staticmethod
    def encode_save_position_zero_msg() -> bytes:
        """Encode save position zero command (sets current position to zero)."""
        return bytes([0xFF] * 7 + [0xFE])

    @staticmethod
    def encode_clear_error_msg() -> bytes:
        """Encode clear error command (clears motor errors like overheating)."""
        return bytes([0xFF] * 7 + [0xFB])

    # -----------------------
    # Sending CAN frames
    # -----------------------
    def send_raw(self, data: bytes, arbitration_id: int | None = None) -> None:
        """
        Send raw CAN message.
        
        Args:
            data: CAN message data bytes (must be 8 bytes)
            arbitration_id: CAN arbitration ID (defaults to motor_id if not specified)
            
        Raises:
            ValueError: If data is not 8 bytes or arbitration_id is invalid
            OSError: If CAN bus error occurs (e.g., Error Code 105 - No buffer space)
            can.CanError: If CAN-specific error occurs
            AttributeError: If bus is not initialized
        """
        if len(data) != 8:
            raise ValueError(f"CAN message data must be 8 bytes, got {len(data)} bytes")
        
        if arbitration_id is None:
            arbitration_id = self.motor_id
        
        if arbitration_id < 0 or arbitration_id > 0x7FF:
            raise ValueError(f"Invalid arbitration_id: {arbitration_id}. Must be in range 0-0x7FF")
        
        try:
            msg = can.Message(arbitration_id=arbitration_id, data=data, is_extended_id=False)
            self.bus.send(msg)
        except OSError as e:
            error_str = str(e)
            errno = getattr(e, 'errno', None)
            
            # Error Code 105: No buffer space available
            if errno == 105 or "Error Code 105" in error_str or "No buffer space available" in error_str or "[Errno 105]" in error_str:
                raise OSError(
                    f"CAN bus buffer full (Error Code 105) when sending to arbitration_id 0x{arbitration_id:03X}. "
                    f"This typically indicates: no motor connected, motor not powered, or CAN hardware issue. "
                    f"Original error: {e}"
                ) from e
            # Other OSError cases
            raise OSError(f"CAN bus system error when sending to arbitration_id 0x{arbitration_id:03X}: {e}") from e
        except can.CanError as e:
            raise can.CanError(f"CAN bus error when sending to arbitration_id 0x{arbitration_id:03X}: {e}") from e
        except AttributeError as e:
            if "bus" in str(e).lower() or "send" in str(e).lower():
                raise AttributeError(f"CAN bus not initialized. Bus may be closed or not connected.") from e
            raise
        except Exception as e:
            raise RuntimeError(f"Unexpected error sending CAN message to arbitration_id 0x{arbitration_id:03X}: {e}") from e

    def enable(self) -> None:
        self.send_raw(self.encode_enable_msg())

    def disable(self) -> None:
        self.send_raw(self.encode_disable_msg())

    def set_zero_position(self) -> None:
        """Set the current output shaft position to zero."""
        self.send_raw(self.encode_save_position_zero_msg())
    
    def set_zero_command(self) -> None:
        """Send zero command (pos=0, vel=0, torq=0, kp=0, kd=0)."""
        self.send_cmd_mit(target_position=0.0, target_velocity=0.0, stiffness=0.0, damping=0.0, feedforward_torque=0.0)

    def ensure_control_mode(self, control_mode: str) -> None:
        """
        Ensure control mode (register 10) matches the desired mode.
        Reads register 10; if it differs, writes and verifies.

        Args:
            control_mode: "MIT", "POS_VEL", "VEL", or "FORCE_POS"

        Raises:
            ValueError: If control_mode is invalid or register value is invalid
            TimeoutError: If reading/writing register times out
            RuntimeError: Other errors during register operations, or if verification after write fails
        """
        mode_to_register = {"MIT": 1, "POS_VEL": 2, "VEL": 3, "FORCE_POS": 4}
        if control_mode not in mode_to_register:
            raise ValueError(f"Invalid control_mode: {control_mode}. Must be one of {list(mode_to_register.keys())}")
        desired = mode_to_register[control_mode]

        try:
            current = int(self.get_register(10, timeout=1.0))
            if current == desired:
                return
            print(f"⚠ Control mode mismatch: register 10 = {current}, required = {desired}")
            print(f"  Setting control mode to {control_mode} (register value: {desired})...")
            self.write_register(10, desired)
            time.sleep(0.1)
            verify = int(self.get_register(10, timeout=1.0))
            if verify != desired:
                raise RuntimeError(
                    f"Control mode verification failed after write: expected {desired}, got {verify}"
                )
            print(f"✓ Control mode set to {control_mode}")
        except TimeoutError as e:
            raise TimeoutError(f"Timeout while checking/setting control mode (register 10): {e}") from e
        except ValueError as e:
            raise ValueError(f"Invalid control mode value in register 10: {e}") from e
        except RuntimeError:
            raise  # verification failure, preserve message
        except Exception as e:
            raise RuntimeError(f"Error checking/setting control mode: {e}") from e

    def set_can_timeout(self, timeout_ms: int) -> None:
        """
        Set CAN timeout alarm time (register 9).
        
        Args:
            timeout_ms: Timeout in milliseconds
        
        Note:
            Register 9 stores timeout in units of 50 microseconds: **1 register unit = 50 microseconds**.
            
            Conversion formula: register_value = timeout_ms × 20
            
            Examples:
            - 1000 ms = 1,000,000 microseconds = 20,000 register units
            - 50 ms = 50,000 microseconds = 1,000 register units
        """
        # Convert milliseconds to register units: 1 register unit = 50 microseconds
        # timeout_ms * 1000 us/ms / 50 us/unit = timeout_ms * 20
        register_value = timeout_ms * 20
        self.write_register(9, register_value)

    def clear_error(self) -> None:
        """Clear motor errors (e.g., overheating)."""
        self.send_raw(self.encode_clear_error_msg())

    def _check_motor_status(self) -> None:
        """Check motor status and enable/clear errors if necessary."""
        # Check if motor is disabled and enable it if necessary
        if self.state and self.state.get("status_code") == DM_MOTOR_DISABLED:
            self.enable()
        
        # Check if motor has lost communication and clear error if necessary
        if self.state and self.state.get("status_code") == DM_MOTOR_LOST_COMM:
            self.clear_error()

    def send_cmd_mit(
        self,
        target_position: float = 0.0,
        target_velocity: float = 0.0,
        stiffness: float = 0.0,
        damping: float = 0.0,
        feedforward_torque: float = 0.0,
    ) -> None:
        """
        Send MIT (Position + Velocity + Torque) control command.
        
        Args:
            target_position: Desired position (radians)
            target_velocity: Desired velocity (rad/s)
            stiffness: Stiffness (kp) for MIT mode
            damping: Damping (kd) for MIT mode
            feedforward_torque: Feedforward torque for MIT mode

        Note:
            Before using this method, ensure that the motor's control mode register (register 10)
            is set to MIT mode (value 1). Use `ensure_control_mode("MIT")` or `set_control_mode(1)`.
        """
        self._check_motor_status()
        data = self.encode_cmd_msg(target_position, target_velocity, feedforward_torque, stiffness, damping)
        self.send_raw(data)

    def send_cmd_pos_vel(
        self,
        target_position: float = 0.0,
        target_velocity: float = 0.0,
    ) -> None:
        """
        Send POS_VEL (Position + Velocity) control command.
        
        Args:
            target_position: Desired position (radians)
            target_velocity: Desired velocity (rad/s)

        Note:
            Before using this method, ensure that the motor's control mode register (register 10)
            is set to POS_VEL mode (value 2). Use `ensure_control_mode("POS_VEL")` or `set_control_mode(2)`.
        """
        self._check_motor_status()
        # POS_VEL Mode: CAN ID 0x100 + motor_id
        data = struct.pack('<ff', target_position, target_velocity)
        arbitration_id = 0x100 + self.motor_id
        self.send_raw(data, arbitration_id=arbitration_id)

    def send_cmd_vel(
        self,
        target_velocity: float = 0.0,
    ) -> None:
        """
        Send VEL (Velocity) control command.
        
        Args:
            target_velocity: Desired velocity (rad/s)

        Note:
            Before using this method, ensure that the motor's control mode register (register 10)
            is set to VEL mode (value 3). Use `ensure_control_mode("VEL")` or `set_control_mode(3)`.
        """
        self._check_motor_status()
        # VEL Mode: CAN ID 0x200 + motor_id
        data = struct.pack('<f', target_velocity) + b'\x00' * 4
        arbitration_id = 0x200 + self.motor_id
        self.send_raw(data, arbitration_id=arbitration_id)

    def send_cmd_force_pos(
        self,
        target_position: float = 0.0,
        velocity_limit: float = 0.0,
        current_limit: float = 0.0,
    ) -> None:
        """
        Send FORCE_POS (Force Position) control command.
        
        Args:
            target_position: Desired position (radians)
            velocity_limit: Velocity limit (rad/s, 0-100) for FORCE_POS mode
            current_limit: Current limit normalized (0.0-1.0) for FORCE_POS mode

        Note:
            Before using this method, ensure that the motor's control mode register (register 10)
            is set to FORCE_POS mode (value 4). Use `ensure_control_mode("FORCE_POS")` or `set_control_mode(4)`.
        """
        self._check_motor_status()
        # FORCE_POS Mode: CAN ID 0x300 + motor_id
        # Clamp and scale velocity limit (0-100 rad/s -> 0-10000)
        v_des_clamped = max(0.0, min(100.0, velocity_limit))
        v_des_scaled = int(v_des_clamped * 100)
        v_des_scaled = min(10000, v_des_scaled)
        
        # Clamp and scale current limit (0.0-1.0 -> 0-10000)
        i_des_clamped = max(0.0, min(1.0, current_limit))
        i_des_scaled = int(i_des_clamped * 10000)
        i_des_scaled = min(10000, i_des_scaled)
        
        # Pack: float (4 bytes) + uint16 (2 bytes) + uint16 (2 bytes)
        data = struct.pack('<fHH', target_position, v_des_scaled, i_des_scaled)
        arbitration_id = 0x300 + self.motor_id
        self.send_raw(data, arbitration_id=arbitration_id)

    def send_cmd(
        self,
        target_position: float = 0.0,
        target_velocity: float = 0.0,
        stiffness: float = 0.0,
        damping: float = 0.0,
        feedforward_torque: float = 0.0,
        control_mode: str = "MIT",
        velocity_limit: float = 0.0,
        current_limit: float = 0.0,
    ) -> None:
        """
        Send command to motor with specified control mode (convenience wrapper).
        
        This method is a convenience wrapper that calls the appropriate mode-specific method.
        For better type safety and clarity, consider using the mode-specific methods directly:
        - `send_cmd_mit()` for MIT mode
        - `send_cmd_pos_vel()` for POS_VEL mode
        - `send_cmd_vel()` for VEL mode
        - `send_cmd_force_pos()` for FORCE_POS mode
        
        Args:
            target_position: Desired position (radians)
            target_velocity: Desired velocity (rad/s)
            stiffness: Stiffness (kp) for MIT mode
            damping: Damping (kd) for MIT mode
            feedforward_torque: Feedforward torque for MIT mode
            control_mode: Control mode - "MIT" (default), "POS_VEL", "VEL", or "FORCE_POS"
            velocity_limit: Velocity limit (rad/s, 0-100) for FORCE_POS mode
            current_limit: Current limit normalized (0.0-1.0) for FORCE_POS mode

        Note:
            Before using this method to send commands, ensure that the motor's control mode register (register 10)
            is set to match the desired control_mode argument ("MIT", "POS_VEL", "VEL", or "FORCE_POS").
            If the register does not match, the motor will not respond to commands and will not move.
        """
        if control_mode == "MIT":
            self.send_cmd_mit(target_position, target_velocity, stiffness, damping, feedforward_torque)
        elif control_mode == "POS_VEL":
            self.send_cmd_pos_vel(target_position, target_velocity)
        elif control_mode == "VEL":
            self.send_cmd_vel(target_velocity)
        elif control_mode == "FORCE_POS":
            self.send_cmd_force_pos(target_position, velocity_limit, current_limit)
        else:
            raise ValueError(f"Unknown control_mode: {control_mode}. Must be 'MIT', 'POS_VEL', 'VEL', or 'FORCE_POS'")

    # -----------------------
    # Decode feedback
    # -----------------------
    def process_feedback_frame(self, data: bytes, arbitration_id: int | None = None) -> None:
        if is_register_reply(data):
            self.decode_register_reply(data, arbitration_id=arbitration_id)
        
        else:
            self.decode_sensor_feedback(data, arbitration_id=arbitration_id)
    
    def decode_register_reply(self, data: bytes, arbitration_id: int | None = None) -> None:
        with self.register_reply_time_lock:
            # record the time of the register reply
            self.register_reply_time[data[3]] = time.perf_counter()
        with self.registers_lock:
            # unpack with corresponding data type
            if REGISTER_TABLE[data[3]].data_type == "float":
                self.registers[data[3]] = struct.unpack("<f", data[4:8])[0]
            elif REGISTER_TABLE[data[3]].data_type == "uint32":
                self.registers[data[3]] = struct.unpack("<I", data[4:8])[0]
            else:
                raise ValueError(f"Unknown data_type: {REGISTER_TABLE[data[3]].data_type} for register {data[3]}")
            return

    def decode_sensor_feedback(self, data: bytes, arbitration_id: int | None = None) -> Dict[str, float]:
        if len(data) != 8:
            raise ValueError("Feedback frame must have length 8")

        can_id = data[0] & 0x0F
        status = data[0] >> 4
        pos_int = (data[1] << 8) | data[2]
        vel_int = (data[3] << 4) | (data[4] >> 4)
        torq_int = ((data[4] & 0xF) << 8) | data[5]
        t_mos = float(data[6])
        t_rotor = float(data[7])

        decoded = {
            "can_id": can_id,
            "arbitration_id": arbitration_id,
            "status": decode_state_name(status),
            "status_code": status,
            "pos": uint_to_float(pos_int, self._p_min, self._p_max, 16),
            "vel": uint_to_float(vel_int, self._v_min, self._v_max, 12),
            "torq": uint_to_float(torq_int, self._t_min, self._t_max, 12),
            "t_mos": t_mos,
            "t_rotor": t_rotor,
        }
        self.state = decoded
        return decoded

    # -----------------------
    # Register read/write operations
    # -----------------------
    def _encode_can_id(self, can_id: int) -> tuple[int, int]:
        """Encode CAN ID into low and high bytes."""
        return can_id & 0xFF, (can_id >> 8) & 0xFF

    def _send_register_cmd(self, cmd_byte: int, rid: int, data: Optional[bytes] = None) -> None:
        """
        Send a register command (read/write/store).
        
        Args:
            cmd_byte: Command byte (0x33 for read, 0x55 for write, 0xAA for store)
            rid: Register ID (0-81)
            data: Optional 4-byte data for write operations
        """
        canid_l, canid_h = self._encode_can_id(self.motor_id)
        
        if data is None:
            # Read or store command - D[4-7] are don't care
            msg_data = bytes([canid_l, canid_h, cmd_byte, rid, 0x00, 0x00, 0x00, 0x00])
        else:
            # Write command - D[4-7] contain the data
            if len(data) != 4:
                raise ValueError("Data must be 4 bytes for write operations")
            msg_data = bytes([canid_l, canid_h, cmd_byte, rid]) + data
        
        self.send_raw(msg_data, arbitration_id=0x7FF)

    def request_register_reading(self, rid: int) -> None:
        """
        Request a register reading from the motor.
        """
        with self.register_request_time_lock:
            self.register_request_time[rid] = time.perf_counter()
        self._send_register_cmd(0x33, rid)

    def get_register(self, rid: int, timeout: float = 1.0) -> float | int:
        """
        Read a register value from the motor.

        If the value is not already cached, sends a read request and waits for the
        controller's background polling to receive the reply. The motor never
        reads from the bus; only the controller's poll_feedback does, avoiding
        multiple consumers.

        Requires the motor to be managed by a DaMiaoController (added via
        controller.add_motor). Standalone motors can only return cached values.

        Args:
            rid: Register ID (0-81)
            timeout: Timeout in seconds to wait for response

        Returns:
            Register value as float or int depending on register data type

        Raises:
            KeyError: If register ID is not in the register table
            RuntimeError: If the motor is not managed by a controller (no background polling)
            TimeoutError: If the register reply was not received within timeout
        """
        if rid not in REGISTER_TABLE:
            raise KeyError(f"Register {rid} not found in register table")
        with self.registers_lock:
            if rid in self.registers:
                return self.registers[rid]
        if getattr(self, "_controller", None) is None:
            raise RuntimeError(
                "get_register requires the motor to be managed by a DaMiaoController "
                "(added via controller.add_motor). The controller's background polling "
                "is the only bus reader; standalone motors cannot block-wait for register replies."
            )
        self.request_register_reading(rid)
        deadline = time.time() + timeout
        while True:
            with self.registers_lock:
                if rid in self.registers:
                    return self.registers[rid]
            if time.time() >= deadline:
                raise TimeoutError(f"Register {rid} not received within {timeout}s")
            time.sleep(0.01)

    def write_register(self, rid: int, value: float | int) -> None:
        """
        Write a value to a register.
        
        Args:
            rid: Register ID (0-81)
            value: Value to write (float or int)
        
        Raises:
            KeyError: If register ID is not in the register table
            ValueError: If register is read-only or value is out of range
        """
        # Check if register exists in table
        if rid not in REGISTER_TABLE:
            raise KeyError(f"Register {rid} not found in register table")
        
        reg_info = REGISTER_TABLE[rid]
        
        # Check if register is writable
        if reg_info.access != "RW":
            raise ValueError(f"Register {rid} ({reg_info.variable}) is read-only (access: {reg_info.access})")
        
        # Encode value to 4 bytes using data type from register table
        if reg_info.data_type == "float":
            data_bytes = struct.pack("<f", float(value))
        elif reg_info.data_type == "uint32":
            data_bytes = struct.pack("<I", int(value))
        else:
            raise ValueError(f"Unknown data_type: {reg_info.data_type} for register {rid}")
        
        # Send write command
        self._send_register_cmd(0x55, rid, data_bytes)
        
        # Wait for echo response (optional - motor echoes back the written data)
        # Note: You may want to verify the echo matches, but for now we just send

    def get_register_info(self, rid: int) -> RegisterInfo:
        """
        Get information about a register.
        
        Args:
            rid: Register ID
        
        Returns:
            RegisterInfo object with register details
        
        Raises:
            KeyError: If register ID is not in the register table
        """
        if rid not in REGISTER_TABLE:
            raise KeyError(f"Register {rid} not found in register table")
        return REGISTER_TABLE[rid]

    def store_parameters(self) -> None:
        """
        Store all parameters to flash memory.
        After successful write, all parameters will be written to the chip.
        """
        self._send_register_cmd(0xAA, 0x01)

    def request_motor_feedback(self) -> None:
        """
        Request motor feedback/status information.
        After successful transmission, the motor driver will return current status information.
        """
        canid_l, canid_h = self._encode_can_id(self.motor_id)
        msg_data = bytes([canid_l, canid_h, 0xCC, 0x00, 0x00, 0x00, 0x00, 0x00])
        self.send_raw(msg_data, arbitration_id=0x7FF)

    def read_all_registers(self, timeout: float = 0.05) -> Dict[int, float | int]:
        """
        Read all registers from the motor.
        
        Args:
            timeout: Timeout in seconds per register read
        
        Returns:
            Dictionary mapping register ID to value
        """
        for rid, reg_info in REGISTER_TABLE.items():
            if reg_info.access in ["RO", "RW"]:  # Readable registers
                self.request_register_reading(rid)
                time.sleep(0.0005)
        results: Dict[int, float | int] = {}
        time.sleep(0.01)  # wait for the replies
        for rid, reg_info in REGISTER_TABLE.items():
            if reg_info.access in ["RO", "RW"]:  # Readable registers
                try:
                    results[rid] = self.get_register(rid, timeout=timeout)
                except (TimeoutError, KeyError, ValueError, RuntimeError) as e:
                    # Store error as string for debugging
                    results[rid] = f"ERROR: {e}"
        return results

    # -----------------------
    # Limit setters and mapping helpers
    # -----------------------
    def set_p_limits(self, p_min: float, p_max: float) -> None:
        """Set position limits used for encode/decode (MIT mode)."""
        self._p_min, self._p_max = p_min, p_max

    def set_v_limits(self, v_min: float, v_max: float) -> None:
        """Set velocity limits used for encode/decode (MIT mode)."""
        self._v_min, self._v_max = v_min, v_max

    def set_t_limits(self, t_min: float, t_max: float) -> None:
        """Set torque limits used for encode/decode (MIT mode)."""
        self._t_min, self._t_max = t_min, t_max

    def set_limits(
        self,
        *,
        p_min: Optional[float] = None,
        p_max: Optional[float] = None,
        v_min: Optional[float] = None,
        v_max: Optional[float] = None,
        t_min: Optional[float] = None,
        t_max: Optional[float] = None,
    ) -> None:
        """Update only the specified P/V/T limits. Omitted keys are left unchanged. kp and kd are fixed (KP_MIN/KP_MAX, KD_MIN/KD_MAX)."""
        if p_min is not None:
            self._p_min = p_min
        if p_max is not None:
            self._p_max = p_max
        if v_min is not None:
            self._v_min = v_min
        if v_max is not None:
            self._v_max = v_max
        if t_min is not None:
            self._t_min = t_min
        if t_max is not None:
            self._t_max = t_max

    # -----------------------
    # Setter methods for all writable registers
    # -----------------------
    def set_under_voltage_protection(self, value: float) -> None:
        """Set under-voltage protection value (register 0)."""
        self.write_register(0, value)

    def set_torque_coefficient(self, value: float) -> None:
        """Set torque coefficient (register 1)."""
        self.write_register(1, value)

    def set_over_temperature_protection(self, value: float) -> None:
        """Set over-temperature protection value (register 2)."""
        self.write_register(2, value)

    def set_over_current_protection(self, value: float) -> None:
        """Set over-current protection value (register 3)."""
        self.write_register(3, value)

    def set_acceleration(self, value: float) -> None:
        """Set acceleration (register 4)."""
        self.write_register(4, value)

    def set_deceleration(self, value: float) -> None:
        """Set deceleration (register 5)."""
        self.write_register(5, value)

    def set_maximum_speed(self, value: float) -> None:
        """Set maximum speed (register 6)."""
        self.write_register(6, value)

    def set_feedback_id(self, value: int) -> None:
        """Set feedback ID (register 7)."""
        self.write_register(7, value)

    def set_receive_id(self, value: int) -> None:
        """Set receive ID (register 8)."""
        self.write_register(8, value)

    def set_timeout_alarm(self, value: int) -> None:
        """
        Set timeout alarm time (register 9).
        
        Args:
            value: Timeout value in register units (1 unit = 50 microseconds)
        
        Note:
            This method writes the raw register value. For convenience, use `set_can_timeout()`
            which accepts milliseconds and handles the conversion automatically.
            
            Conversion: 1 register unit = 50 microseconds
            To convert from milliseconds: register_value = timeout_ms × 20
        """
        self.write_register(9, value)

    def set_control_mode(self, value: int) -> None:
        """Set control mode (register 10)."""
        self.write_register(10, value)

    def set_position_mapping_range(self, value: float) -> None:
        """Set position mapping range (register 21)."""
        self.write_register(21, value)

    def set_speed_mapping_range(self, value: float) -> None:
        """Set speed mapping range (register 22)."""
        self.write_register(22, value)

    def set_torque_mapping_range(self, value: float) -> None:
        """Set torque mapping range (register 23)."""
        self.write_register(23, value)

    def set_current_loop_bandwidth(self, value: float) -> None:
        """Set current loop control bandwidth (register 24)."""
        self.write_register(24, value)

    def set_speed_loop_kp(self, value: float) -> None:
        """Set speed loop proportional gain Kp (register 25)."""
        self.write_register(25, value)

    def set_speed_loop_ki(self, value: float) -> None:
        """Set speed loop integral gain Ki (register 26)."""
        self.write_register(26, value)

    def set_position_loop_kp(self, value: float) -> None:
        """Set position loop proportional gain Kp (register 27)."""
        self.write_register(27, value)

    def set_position_loop_ki(self, value: float) -> None:
        """Set position loop integral gain Ki (register 28)."""
        self.write_register(28, value)

    def set_overvoltage_protection(self, value: float) -> None:
        """Set overvoltage protection value (register 29)."""
        self.write_register(29, value)

    def set_gear_efficiency(self, value: float) -> None:
        """Set gear torque efficiency (register 30)."""
        self.write_register(30, value)

    def set_speed_loop_damping(self, value: float) -> None:
        """Set speed loop damping coefficient (register 31)."""
        self.write_register(31, value)

    def set_speed_loop_filter_bandwidth(self, value: float) -> None:
        """Set speed loop filter bandwidth (register 32)."""
        self.write_register(32, value)

    def set_current_loop_enhancement(self, value: float) -> None:
        """Set current loop enhancement coefficient (register 33)."""
        self.write_register(33, value)

    def set_speed_loop_enhancement(self, value: float) -> None:
        """Set speed loop enhancement coefficient (register 34)."""
        self.write_register(34, value)

    def set_can_baud_rate(self, baud_rate_code: int) -> None:
        """
        Set CAN baud rate using register 35 (can_br).
        
        Args:
            baud_rate_code: Baud rate code (0=125K, 1=200K, 2=250K, 3=500K, 4=1M)
        
        Raises:
            ValueError: If baud_rate_code is not in valid range [0, 4]
        """
        if baud_rate_code not in CAN_BAUD_RATE_CODES:
            raise ValueError(f"Invalid baud rate code: {baud_rate_code}. Must be in {list(CAN_BAUD_RATE_CODES.keys())}")
        
        self.write_register(35, baud_rate_code)  # Register 35 is can_br
        self.store_parameters()  # Store to flash so it persists



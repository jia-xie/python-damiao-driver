#!/usr/bin/env python3
"""
Display utilities for CLI output: ANSI colors, box drawing, and formatted printing.
"""
import re
import subprocess
import sys
import time
from typing import Any, Dict, Set

import can

from damiao_motor.core.controller import DaMiaoController
from damiao_motor.core.motor import DaMiaoMotor, REGISTER_TABLE

# ANSI color codes
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
BRIGHT_CYAN = "\033[1;96m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Box drawing characters
BOX_HORIZONTAL = "─"
BOX_VERTICAL = "│"
BOX_CORNER_TL = "┌"
BOX_CORNER_TR = "┐"
BOX_CORNER_BL = "└"
BOX_CORNER_BR = "┘"
BOX_JOIN_LEFT = "├"  # Connects vertical line to horizontal line (right)
BOX_JOIN_RIGHT = "┤"  # Connects vertical line to horizontal line (left)


def strip_ansi_codes(text: str) -> str:
    """Remove ANSI escape sequences from a string."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


def pad_with_ansi(text: str, width: int) -> str:
    """
    Pad a string to a specific visible width, accounting for ANSI color codes.
    
    Args:
        text: String that may contain ANSI color codes
        width: Desired visible width
        
    Returns:
        Padded string with correct visible width
    """
    visible_length = len(strip_ansi_codes(text))
    padding_needed = max(0, width - visible_length)
    return text + (' ' * padding_needed)


def print_boxed(title: str, width: int = 60, color: str = "", border_color: str = "") -> None:
    """
    Print a title in a box with borders.
    
    Args:
        title: Title text to display
        width: Width of the box (default: 60)
        color: Color code for the title text
        border_color: Color code for the border
    """
    border = border_color if border_color else ""
    title_color = color if color else ""
    reset = RESET
    
    top_border = f"{border}{BOX_CORNER_TL}{BOX_HORIZONTAL * (width - 2)}{BOX_CORNER_TR}{reset}"
    title_line = f"{border}{BOX_VERTICAL}{reset} {title_color}{title:<{width-4}}{reset} {border}{BOX_VERTICAL}{reset}"
    bottom_border = f"{border}{BOX_CORNER_BL}{BOX_HORIZONTAL * (width - 2)}{BOX_CORNER_BR}{reset}"
    
    print(top_border)
    print(title_line)
    print(bottom_border)


def print_section_header(title: str, width: int = 80) -> None:
    """
    Print a section header with box top borders (bottom border should be closed separately).
    
    Args:
        title: Section title
        width: Width of the box (default: 80)
    """
    print()
    print_boxed(title, width=width, color=GREEN)


def print_error_box(title: str, lines: list[str], width: int = 60) -> None:
    """
    Print an error message in a box.
    
    Args:
        title: Error title
        lines: List of error message lines
        width: Width of the box (default: 60)
    """
    print()
    border = RED
    reset = RESET
    
    top_border = f"{border}{BOX_CORNER_TL}{BOX_HORIZONTAL * (width - 2)}{BOX_CORNER_TR}{reset}"
    print(top_border)
    
    title_line = f"{border}{BOX_VERTICAL}{reset} {RED}{title:<{width-4}}{reset} {border}{BOX_VERTICAL}{reset}"
    print(title_line)
    
    for line in lines:
        line_content = f"{border}{BOX_VERTICAL}{reset} {line:<{width-4}}{reset} {border}{BOX_VERTICAL}{reset}"
        print(line_content)
    
    bottom_border = f"{border}{BOX_CORNER_BL}{BOX_HORIZONTAL * (width - 2)}{BOX_CORNER_BR}{reset}"
    print(bottom_border)


def print_warning_box(title: str, lines: list[str], width: int = 60) -> None:
    """
    Print a warning message in a box.
    
    Args:
        title: Warning title
        lines: List of warning message lines
        width: Width of the box (default: 60)
    """
    print()
    border = YELLOW
    reset = RESET
    
    top_border = f"{border}{BOX_CORNER_TL}{BOX_HORIZONTAL * (width - 2)}{BOX_CORNER_TR}{reset}"
    print(top_border)
    
    title_line = f"{border}{BOX_VERTICAL}{reset} {YELLOW}{title:<{width-4}}{reset} {border}{BOX_VERTICAL}{reset}"
    print(title_line)
    
    for line in lines:
        line_content = f"{border}{BOX_VERTICAL}{reset} {line:<{width-4}}{reset} {border}{BOX_VERTICAL}{reset}"
        print(line_content)
    
    bottom_border = f"{border}{BOX_CORNER_BL}{BOX_HORIZONTAL * (width - 2)}{BOX_CORNER_BR}{reset}"
    print(bottom_border)


def print_motor_state(state: Dict[str, Any]) -> None:
    """
    Print motor state information in a formatted string.
    
    Args:
        state: Dictionary containing motor state information with keys:
            - status_code: Motor status code
            - status: Motor status name
            - pos: Position in radians
            - vel: Velocity in rad/s
            - torq: Torque in Nm
            - t_mos: MOSFET temperature in °C
            - t_rotor: Rotor temperature in °C
    """
    status_code = state.get("status_code", "N/A")
    status_name = state.get("status", "UNKNOWN")
    print(f"State: {status_code} ({status_name}) | "
          f"Pos:{state.get('pos', 0.0): 8.3f} rad | "
          f"Vel:{state.get('vel', 0.0): 8.3f} rad/s | "
          f"Torq:{state.get('torq', 0.0): 8.3f} Nm | "
          f"T_mos:{state.get('t_mos', 0.0):5.1f}°C | "
          f"T_rotor:{state.get('t_rotor', 0.0):5.1f}°C")


def check_and_bring_up_can_interface(channel: str, bitrate: int = 1000000) -> bool:
    """
    Check if CAN interface is up, and bring it up if it's down.
    
    Args:
        channel: CAN channel name (e.g., "can0")
        bitrate: CAN bitrate in bits per second (default: 1000000)
    
    Returns:
        True if interface is up (or successfully brought up), False otherwise
    """
    try:
        # Check if interface exists and is up
        result = subprocess.run(
            ["ip", "link", "show", channel],
            capture_output=True,
            text=True,
            check=False,
        )
        
        if result.returncode != 0:
            # Interface does not exist - return False
            # Note: Caller should handle printing status within box
            return False
        
        # Check if interface is UP
        if "state UP" in result.stdout or "state UNKNOWN" in result.stdout:
            # Interface exists and is up, but verify it's actually a CAN interface
            if "link/can" not in result.stdout:
                # Reconfigure it (caller handles status printing)
                subprocess.run(
                    ["sudo", "ip", "link", "set", channel, "down"],
                    check=False,
                )
                subprocess.run(
                    ["sudo", "ip", "link", "set", channel, "type", "can", "bitrate", str(bitrate)],
                    check=True,
                )
                subprocess.run(
                    ["sudo", "ip", "link", "set", channel, "up"],
                    check=True,
                )
                time.sleep(0.5)
            return True
        elif "state DOWN" in result.stdout:
            # Set it down first (in case it needs reconfiguration)
            subprocess.run(
                ["sudo", "ip", "link", "set", channel, "down"],
                check=False,  # Don't fail if already down
            )
            # Configure and bring up the interface with specified bitrate
            subprocess.run(
                ["sudo", "ip", "link", "set", channel, "type", "can", "bitrate", str(bitrate)],
                check=True,
            )
            subprocess.run(
                ["sudo", "ip", "link", "set", channel, "up"],
                check=True,
            )
            time.sleep(0.5)  # Give it a moment to initialize
            # Verify it's actually up
            verify = subprocess.run(
                ["ip", "link", "show", channel],
                capture_output=True,
                text=True,
                check=False,
            )
            if verify.returncode == 0 and "state UP" in verify.stdout:
                return True
            else:
                return False
        else:
            # Try to bring it up anyway with full configuration
            subprocess.run(
                ["sudo", "ip", "link", "set", channel, "down"],
                check=False,
            )
            subprocess.run(
                ["sudo", "ip", "link", "set", channel, "type", "can", "bitrate", str(bitrate)],
                check=False,
            )
            subprocess.run(
                ["sudo", "ip", "link", "set", channel, "up"],
                check=False,
            )
            time.sleep(0.5)
            return True
            
    except subprocess.CalledProcessError as e:
        # Caller handles printing
        return False
    except FileNotFoundError:
        # Caller handles printing
        return False
    except Exception as e:
        # Caller handles printing
        return False


def scan_motors(
    channel: str = "can0",
    bustype: str = "socketcan",
    motor_ids: list[int] | None = None,
    duration_s: float = 3.0,
    bitrate: int = 1000000,
    debug: bool = False,
    *,
    motor_type: str = "4310",
) -> Set[int]:
    """
    Scan for connected motors by sending zero commands and listening for feedback.

    Args:
        channel: CAN channel (e.g., "can0")
        bustype: CAN bus type (e.g., "socketcan")
        motor_ids: List of motor IDs to test. If None, tests IDs 0x01-0x10.
        duration_s: How long to listen for responses (seconds)
        motor_type: Motor type for P/V/T presets (e.g. 4340, 4310, 3507). 
                    Defaults to "4310". Only used for encoding zero commands; 
                    doesn't affect which motors are detected.

    Returns:
        Set of motor IDs that responded with feedback.
    """
    if motor_ids is None:
        motor_ids = list(range(0x01, 0x11))  # Test IDs 1-16

    # Open scan status box (80 chars wide, 78 interior)
    print(f"{BOX_CORNER_TL}{BOX_HORIZONTAL * 78}{BOX_CORNER_TR}")
    
    # Check and bring up CAN interface if needed (only for socketcan)
    if bustype == "socketcan":
        line_text = f" Checking CAN interface {channel}..."
        print(f"{BOX_VERTICAL}{pad_with_ansi(line_text, 78)}{BOX_VERTICAL}")
        if not check_and_bring_up_can_interface(channel, bitrate=bitrate):
            warning_text = f" {YELLOW}⚠ Warning: Could not verify {channel} is ready. Continuing anyway...{RESET}"
            print(f"{BOX_VERTICAL}{pad_with_ansi(warning_text, 78)}{BOX_VERTICAL}")
        else:
            # Verify interface is actually up and working
            verify_result = subprocess.run(
                ["ip", "link", "show", channel],
                capture_output=True,
                text=True,
                check=False,
            )
            if verify_result.returncode == 0 and "state UP" in verify_result.stdout:
                ready_text = f" {GREEN}✓ CAN interface {channel} is ready{RESET}"
                print(f"{BOX_VERTICAL}{pad_with_ansi(ready_text, 78)}{BOX_VERTICAL}")
            else:
                warning_text = f" {YELLOW}⚠ Warning: {channel} may not be properly configured{RESET}"
                print(f"{BOX_VERTICAL}{pad_with_ansi(warning_text, 78)}{BOX_VERTICAL}")

    controller = DaMiaoController(channel=channel, bustype=bustype)
    
    # Flush any pending messages from the bus
    line_text = f" Flushing CAN bus buffer..."
    print(f"{BOX_VERTICAL}{pad_with_ansi(line_text, 78)}{BOX_VERTICAL}")
    flushed_count = controller.flush_bus()
    if flushed_count > 0:
        flushed_text = f"   {GREEN}Flushed {flushed_count} pending message(s) from bus{RESET}"
        print(f"{BOX_VERTICAL}{pad_with_ansi(flushed_text, 78)}{BOX_VERTICAL}")
    else:
        line_text = f"   Bus buffer is clean"
        print(f"{BOX_VERTICAL}{pad_with_ansi(line_text, 78)}{BOX_VERTICAL}")
    
    motors: dict[int, DaMiaoMotor] = {}

    # Create motor instances for all IDs we want to test
    for motor_id in motor_ids:
        try:
            motor = controller.add_motor(motor_id=motor_id, feedback_id=0x00, motor_type=motor_type)
            motors[motor_id] = motor
        except ValueError:
            # Motor already exists, skip
            pass

    # Send zero command to all motors
    line_text = f" Sending zero command to {len(motors)} potential motor IDs..."
    print(f"{BOX_VERTICAL}{pad_with_ansi(line_text, 78)}{BOX_VERTICAL}")
    try:
        for motor in motors.values():
            motor.send_cmd_mit(target_position=0.0, target_velocity=0.0, stiffness=0.0, damping=0.0, feedforward_torque=0.0)
            if debug:
                # Print sent command in debug mode
                cmd_data = motor.encode_cmd_msg(0.0, 0.0, 0.0, 0.0, 0.0)
                data_hex = " ".join(f"{b:02X}" for b in cmd_data)
                sent_text = f"   [SENT] 0x{motor.motor_id:03X} [{data_hex}]"
                print(f"{BOX_VERTICAL}{pad_with_ansi(sent_text, 78)}{BOX_VERTICAL}")
    except Exception as e:
        error_str = str(e)
        if "Error Code 80" in error_str or "No buffer space available" in error_str or "[Errno 80]" in error_str:
            error_lines = [
                "Original error: " + str(e),
                "",
                "This error typically indicates:",
                "  • No CAN device (motor) is connected to the bus",
                "  • Motor(s) are not powered on",
                "  • CAN interface hardware issue",
                "",
                "Please check:",
                "  1. Motor(s) are properly connected to the CAN bus",
                "  2. Motor(s) are powered on",
                "  3. CAN interface hardware is working correctly",
                "  4. CAN bus termination resistors (120Ω) are installed at both ends",
            ]
            print_error_box("[ERROR CODE 80] No buffer space available when sending commands", error_lines, width=70)
            # Clean up and exit gracefully
            try:
                controller.bus.shutdown()
            except:
                pass
            sys.exit(1)
        else:
            raise

    # Listen for feedback
    line_text = f" Listening for responses for {duration_s} seconds..."
    print(f"{BOX_VERTICAL}{pad_with_ansi(line_text, 78)}{BOX_VERTICAL}")
    start_time = time.perf_counter()
    responded_ids: Set[int] = set()
    debug_messages = []  # Collect debug messages if debug mode is enabled
    # Track seen motor IDs and arbitration IDs for conflict detection
    seen_motor_ids: Set[int] = set()  # Track decoded motor IDs (logical_id)
    seen_arbitration_ids: Set[int] = set()  # Track arbitration IDs
    # Collect conflicts to group them at the end
    conflicted_motor_ids: Set[int] = set()  # Motor IDs that appeared multiple times
    conflicted_arbitration_ids: Set[int] = set()  # Arbitration IDs that appeared multiple times
    # Collect motor register information for table display
    motor_registers: Dict[int, Dict[int, float | int]] = {}  # motor_id -> {rid -> value}

    while time.perf_counter() - start_time < duration_s:
        # Debug mode: collect and print raw messages immediately
        if debug:
            # Read and collect raw messages, then process normally
            while True:
                msg = controller.bus.recv(timeout=0)
                if msg is None:
                    break
                data_hex = " ".join(f"{b:02X}" for b in msg.data)
                debug_msg = f"  0x{msg.arbitration_id:03X} [{data_hex}]"
                debug_messages.append(debug_msg)
                # Print immediately in debug mode
                print(debug_msg)
                # Process the message manually for debug mode
                if len(msg.data) == 8:
                    logical_id = msg.data[0] & 0x0F
                    arb_id = msg.arbitration_id
                    
                    # Check for motor ID conflict (same decoded motor ID seen twice)
                    if logical_id in seen_motor_ids:
                        conflicted_motor_ids.add(logical_id)
                    
                    # Check for arbitration ID conflict (same arbitration ID seen twice)
                    if arb_id in seen_arbitration_ids:
                        conflicted_arbitration_ids.add(arb_id)
                    
                    seen_motor_ids.add(logical_id)
                    seen_arbitration_ids.add(arb_id)
                    
                    motor = controller._motors_by_feedback.get(logical_id)
                    if motor is not None:
                        motor.decode_sensor_feedback(bytes(msg.data), arbitration_id=arb_id)
        else:
            # Normal mode: read messages, check conflicts, then process
            while True:
                msg = controller.bus.recv(timeout=0)
                if msg is None:
                    break
                
                if len(msg.data) == 8:
                    logical_id = msg.data[0] & 0x0F
                    arb_id = msg.arbitration_id
                    
                    # Check for motor ID conflict (same decoded motor ID seen twice)
                    if logical_id in seen_motor_ids:
                        conflicted_motor_ids.add(logical_id)
                    
                    # Check for arbitration ID conflict (same arbitration ID seen twice)
                    if arb_id in seen_arbitration_ids:
                        conflicted_arbitration_ids.add(arb_id)
                    
                    seen_motor_ids.add(logical_id)
                    seen_arbitration_ids.add(arb_id)
                    
                    # Process through controller
                    motor = controller._motors_by_feedback.get(logical_id)
                    if motor is not None:
                        motor.decode_sensor_feedback(bytes(msg.data), arbitration_id=arb_id)

        # Check which motors have received feedback
        for motor_id, motor in motors.items():
            if motor.state and motor.state.get("can_id") is not None:
                # Print once per motor when first detected
                if motor_id not in responded_ids:
                    state_name = motor.state.get("status", "UNKNOWN")
                    pos = motor.state.get("pos", 0.0)
                    arb_id = motor.state.get("arbitration_id")
                    if arb_id is not None:
                        motor_text = f"   {GREEN}✓ Motor ID 0x{motor_id:02X}{RESET} responded (arb_id: 0x{arb_id:03X}, state: {state_name}, pos: {pos:.3f})"
                        print(f"{BOX_VERTICAL}{pad_with_ansi(motor_text, 78)}{BOX_VERTICAL}")
                    else:
                        motor_text = f"   {GREEN}✓ Motor ID 0x{motor_id:02X}{RESET} responded (state: {state_name}, pos: {pos:.3f})"
                        print(f"{BOX_VERTICAL}{pad_with_ansi(motor_text, 78)}{BOX_VERTICAL}")
                
                responded_ids.add(motor_id)

        time.sleep(0.01)

    # Print conflicts (grouped)
    if conflicted_motor_ids:
        error_lines = [
            "Multiple motors responded with the same motor ID.",
            "This indicates multiple motors are configured with the same motor ID.",
            f"Conflicted Motor IDs: {', '.join(f'0x{mid:02X}' for mid in sorted(conflicted_motor_ids))}"
        ]
        print_error_box("[ERROR] Motor ID Conflicts Detected", error_lines)
    
    if conflicted_arbitration_ids:
        warning_lines = [
            "Same arbitration ID seen multiple times.",
            "This may indicate a CAN bus configuration issue.",
            f"Conflicted Arbitration IDs: {', '.join(f'0x{aid:03X}' for aid in sorted(conflicted_arbitration_ids))}"
        ]
        print_warning_box("[WARNING] Arbitration ID Conflicts Detected", warning_lines)

    # Close the scan status box
    print(f"{BOX_CORNER_BL}{BOX_HORIZONTAL * 78}{BOX_CORNER_BR}")
    
    # Read all registers from detected motors if no motor ID conflicts
    if not conflicted_motor_ids and responded_ids:
        print("Reading register parameters from detected motors...")
        for motor_id in sorted(responded_ids):
            motor = motors.get(motor_id)
            if motor is not None:
                try:
                    registers = motor.read_all_registers(timeout=0.05)
                    motor_registers[motor_id] = registers
                except Exception as e:
                    print(f"  {YELLOW}⚠ Failed to read registers from motor 0x{motor_id:02X}: {e}{RESET}")
        print()

    # Print motor register table if no motor ID conflicts
    if not conflicted_motor_ids and motor_registers:
        # Start register table box
        print()
        top_border = f"{BOX_CORNER_TL}{BOX_HORIZONTAL * 78}{BOX_CORNER_TR}"
        print(top_border)
        # Header line
        header_text = f" {GREEN}Detected Motors - Register Parameters{RESET}"
        print(f"{BOX_VERTICAL}{pad_with_ansi(header_text, 78)}{BOX_VERTICAL}")
        
        # Group registers by motor
        for motor_id in sorted(motor_registers.keys()):
            registers = motor_registers[motor_id]
            # Separator line before motor section
            print(f"{BOX_JOIN_LEFT}{BOX_HORIZONTAL * 78}{BOX_JOIN_RIGHT}")
            # Motor ID header - use pad_with_ansi to account for color codes
            motor_id_text = f" {GREEN}Motor ID: 0x{motor_id:02X} ({motor_id}){RESET}"
            print(f"{BOX_VERTICAL}{pad_with_ansi(motor_id_text, 78)}{BOX_VERTICAL}")
            # Separator line
            print(f"{BOX_JOIN_LEFT}{BOX_HORIZONTAL * 78}{BOX_JOIN_RIGHT}")
            # Table header - adjust column widths to fit within 78 chars
            # Format: " RID(4) Var(10) Desc(32) Value(12) Type(8) Access(6)" = 78 total
            # Calculation: 1+4+1+10+1+32+1+12+1+8+1+6 = 78
            header_content = f" {'RID':<4} {'Variable':<10} {'Description':<32} {'Value':<12} {'Type':<8} {'Access':<6}"
            print(f"{BOX_VERTICAL}{pad_with_ansi(header_content, 78)}{BOX_VERTICAL}")
            # Header separator
            print(f"{BOX_JOIN_LEFT}{BOX_HORIZONTAL * 78}{BOX_JOIN_RIGHT}")
            
            for rid in sorted(registers.keys()):
                if rid not in REGISTER_TABLE:
                    continue
                
                reg_info = REGISTER_TABLE[rid]
                value = registers[rid]
                
                # Format value based on type
                if isinstance(value, str) and value.startswith("ERROR"):
                    value_str = value
                elif reg_info.data_type == "float":
                    value_str = f"{float(value):.2f}"
                else:
                    value_str = str(int(value))
                
                # Truncate long descriptions to fit (32 chars for desc column)
                desc = reg_info.description[:30] + ".." if len(reg_info.description) > 32 else reg_info.description
                
                # Format table row - match header column widths
                row_content = f" {rid:<4} {reg_info.variable:<10} {desc:<32} {value_str:<12} {reg_info.data_type:<8} {reg_info.access:<6}"
                print(f"{BOX_VERTICAL}{pad_with_ansi(row_content, 78)}{BOX_VERTICAL}")
        
        # Close the box
        print(f"{BOX_CORNER_BL}{BOX_HORIZONTAL * 78}{BOX_CORNER_BR}")

    # Print debug summary if messages were collected
    if debug and debug_messages:
        print()
        print_section_header(f"DEBUG: Total {len(debug_messages)} raw CAN messages received", width=80)
        print(f"{BOX_CORNER_BL}{BOX_HORIZONTAL * 78}{BOX_CORNER_BR}")

    # Cleanup
    try:
        controller.bus.shutdown()
    except:
        pass

    return responded_ids

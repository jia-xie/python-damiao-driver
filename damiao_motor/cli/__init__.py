#!/usr/bin/env python3
"""
CLI tool for DaMiao motors.
"""
import argparse
import sys

from damiao_motor import __version__
from .commands import (
    cmd_scan,
    cmd_set_zero,
    cmd_set_zero_position,
    cmd_set_can_timeout,
    cmd_set_motor_id,
    cmd_set_feedback_id,
    cmd_send_cmd_mit,
    cmd_send_cmd_pos_vel,
    cmd_send_cmd_vel,
    cmd_send_cmd_force_pos,
    cmd_gui,
)
from .formatter import ColorizedHelpFormatter

def unified_main() -> None:
    """
    Unified CLI entry point with subcommands.
    
    Main entry point for the `damiao` command-line tool. Provides a unified interface
    for scanning, configuring, and controlling DaMiao motors over CAN bus.
    
    Available commands:
        - scan: Scan for connected motors
        - send-cmd-mit: Send MIT control mode command
        - send-cmd-pos-vel: Send POS_VEL control mode command
        - send-cmd-vel: Send VEL control mode command
        - send-cmd-force-pos: Send FORCE_POS control mode command
        - set-zero-command: Send zero command continuously
        - set-zero-position: Set current position to zero
        - set-can-timeout: Set CAN timeout alarm time
        - set-motor-id: Change motor receive ID
        - set-feedback-id: Change motor feedback ID
        - gui: Launch web-based GUI for motor control
    
    Global options (available for all commands):
        - --version: Show version number and exit
        - --channel: CAN channel (default: can0)
        - --bustype: CAN bus type (default: socketcan)
        - --bitrate: CAN bitrate in bits per second (default: 1000000)
    
    Examples:
        ```bash
        # Scan for motors
        damiao scan
        
        # Send MIT command
        damiao send-cmd-mit --id 1 --position 1.5 --velocity 0.0 --stiffness 3.0 --damping 0.5
        
        # Set current position to zero
        damiao set-zero-position --id 1
        ```
    """
    parser = argparse.ArgumentParser(
        description="DaMiao Motor CLI Tool - Control and configure DaMiao motors over CAN bus",
        formatter_class=ColorizedHelpFormatter,
        epilog="""
For more information about a specific command, use:
  damiao <command> --help
        """,
    )
    
    # Global arguments
    parser.add_argument(
        "--version",
        action="version",
        version=f"{__version__}",
        help="Show version number",
    )
    parser.add_argument(
        "--channel",
        type=str,
        default="can0",
        help="CAN channel (default: can0)",
    )
    parser.add_argument(
        "--bustype",
        type=str,
        default="socketcan",
        help="CAN bus type (default: socketcan)",
    )
    parser.add_argument(
        "--bitrate",
        type=int,
        default=1000000,
        help="CAN bitrate in bits per second (default: 1000000). Only used when bringing up interface.",
    )
    
    subparsers = parser.add_subparsers(
        dest="command",
        help="Available commands",
        required=True,
        metavar="COMMAND",
        title="Commands",
        description="Use 'damiao <command> --help' for more information about a specific command."
    )
    
    # gui command (highlighted - listed first)
    gui_parser = subparsers.add_parser(
        "gui",
        help="Launch web-based GUI for motor control (recommended)",
        description="Launch the web-based GUI for viewing and controlling DaMiao motors.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start GUI on default host and port (http://127.0.0.1:5000)
  damiao gui

  # Start GUI on custom port
  damiao gui --port 8080

  # Start GUI on all interfaces
  damiao gui --host 0.0.0.0

  # Start GUI with production server (requires waitress)
  damiao gui --production

  # Start GUI with debug mode
  damiao gui --debug
        """
    )
    gui_parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    gui_parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to bind to (default: 5000)",
    )
    gui_parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )
    gui_parser.add_argument(
        "--production",
        action="store_true",
        help="Use production WSGI server (requires waitress)",
    )
    gui_parser.set_defaults(func=cmd_gui)
    
    # Helper function to add global arguments to subcommands
    def add_global_args(subparser):
        """Add global arguments to a subcommand parser."""
        subparser.add_argument(
            "--channel",
            type=str,
            default="can0",
            help="CAN channel (default: can0)",
        )
        subparser.add_argument(
            "--bustype",
            type=str,
            default="socketcan",
            help="CAN bus type (default: socketcan)",
        )
        subparser.add_argument(
            "--bitrate",
            type=int,
            default=1000000,
            help="CAN bitrate in bits per second (default: 1000000). Only used when bringing up interface.",
        )
        subparser.add_argument(
            "--motor-type",
            type=str,
            default="4340",
            choices=["4310", "4310P", "4340", "4340P", "6006", "8006", "8009", "10010L", "10010", "H3510", "G6215", "H6220", "JH11", "6248P", "3507"],
            dest="motor_type",
            help="Motor type for P/V/T presets (e.g. 4340, 4310, 3507). Defaults to 4340. Only needed for encoding commands; doesn't affect which motors are detected during scan.",
        )
    
    # scan command
    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan for connected motors on CAN bus",
        description="Scan for connected motors on CAN bus by sending zero commands and listening for responses.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan default ID range (0x01-0x10) - motor-type is optional
  damiao scan

  # Scan specific motor IDs
  damiao scan --ids 1 2 3

  # Scan with longer listen duration
  damiao scan --duration 2.0

  # Scan with specific motor type (optional, defaults to 4310)
  damiao scan --motor-type 4340

  # Scan with debug output (print all raw CAN messages)
  damiao scan --debug
        """
    )
    scan_parser.add_argument(
        "--ids",
        type=int,
        nargs="+",
        metavar="ID",
        help="Motor IDs to test (e.g., --ids 1 2 3). If not specified, tests IDs 0x01-0x10.",
    )
    scan_parser.add_argument(
        "--duration",
        type=float,
        default=0.5,
        help="Duration to listen for responses in seconds (default: 0.5)",
    )
    scan_parser.add_argument(
        "--debug",
        action="store_true",
        help="Print all raw CAN messages for debugging.",
    )
    # Add global args (channel, bustype, bitrate) but NOT motor-type
    scan_parser.add_argument(
        "--channel",
        type=str,
        default="can0",
        help="CAN channel (default: can0)",
    )
    scan_parser.add_argument(
        "--bustype",
        type=str,
        default="socketcan",
        help="CAN bus type (default: socketcan)",
    )
    scan_parser.add_argument(
        "--bitrate",
        type=int,
        default=1000000,
        help="CAN bitrate in bits per second (default: 1000000). Only used when bringing up interface.",
    )
    # Motor type is optional for scan (defaults to 4310)
    scan_parser.add_argument(
        "--motor-type",
        type=str,
        default="4310",
        choices=["4310", "4310P", "4340", "4340P", "6006", "8006", "8009", "10010L", "10010", "H3510", "G6215", "H6220", "JH11", "6248P", "3507"],
        dest="motor_type",
        help="Motor type for P/V/T presets (default: 4310). Only used for encoding zero commands; doesn't affect which motors are detected.",
    )
    scan_parser.set_defaults(func=cmd_scan)
    
    # set-zero-command (renamed from set-zero)
    zero_parser = subparsers.add_parser(
        "set-zero-command",
        help="Send zero command to a motor",
        description="Send a zero command continuously to a motor.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Send zero command continuously (loops until Ctrl+C)
  damiao set-zero-command --id 1

  # With custom frequency
  damiao set-zero-command --id 1 --frequency 50.0
        """
    )
    zero_parser.add_argument(
        "--id",
        type=int,
        required=True,
        dest="motor_id",
        help="Motor ID to send zero command to",
    )
    zero_parser.add_argument(
        "--frequency",
        type=float,
        default=100.0,
        help="Command frequency in Hz (default: 100.0)",
    )
    add_global_args(zero_parser)
    zero_parser.set_defaults(func=cmd_set_zero)
    
    # set-zero-position command
    zero_pos_parser = subparsers.add_parser(
        "set-zero-position",
        help="Set current position to zero",
        description="Set the current output shaft position to zero (save position zero).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Set current position to zero
  damiao set-zero-position --id 1
        """
    )
    zero_pos_parser.add_argument(
        "--id",
        type=int,
        required=True,
        dest="motor_id",
        help="Motor ID",
    )
    add_global_args(zero_pos_parser)
    zero_pos_parser.set_defaults(func=cmd_set_zero_position)
    
    # set-can-timeout command
    timeout_parser = subparsers.add_parser(
        "set-can-timeout",
        help="Set CAN timeout alarm time (register 9)",
        description="Set the CAN timeout alarm time in milliseconds. Register 9 uses units of 50 microseconds (1 unit = 50us).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Set CAN timeout to 1000 ms
  damiao set-can-timeout --id 1 --timeout 1000
        """
    )
    timeout_parser.add_argument(
        "--id",
        type=int,
        required=True,
        dest="motor_id",
        help="Motor ID",
    )
    timeout_parser.add_argument(
        "--timeout",
        type=int,
        required=True,
        dest="timeout_ms",
        help="Timeout in milliseconds (ms)",
    )
    add_global_args(timeout_parser)
    timeout_parser.set_defaults(func=cmd_set_can_timeout)
    
    # set-motor-id command
    set_motor_id_parser = subparsers.add_parser(
        "set-motor-id",
        help="Set motor receive ID (register 8)",
        description="Change the motor's receive ID (ESC_ID, register 8). This is the ID used to send commands to the motor.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Change motor ID from 1 to 2
  damiao set-motor-id --current 1 --target 2

Note: After changing the motor ID, you will need to use the new ID to communicate with the motor.
        """
    )
    set_motor_id_parser.add_argument(
        "--current",
        type=int,
        required=True,
        help="Current motor ID (to connect to the motor)",
    )
    set_motor_id_parser.add_argument(
        "--target",
        type=int,
        required=True,
        help="Target motor ID (new receive ID)",
    )
    add_global_args(set_motor_id_parser)
    set_motor_id_parser.set_defaults(func=cmd_set_motor_id)
    
    # set-feedback-id command
    set_feedback_id_parser = subparsers.add_parser(
        "set-feedback-id",
        help="Set motor feedback ID (register 7)",
        description="Change the motor's feedback ID (MST_ID, register 7). This is the ID used to identify feedback messages from the motor.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Change feedback ID to 3 (using motor ID 1 to connect)
  damiao set-feedback-id --current 1 --target 3

Note: The motor will now respond with feedback using the new feedback ID.
        """
    )
    set_feedback_id_parser.add_argument(
        "--current",
        type=int,
        required=True,
        help="Current motor ID (to connect to the motor)",
    )
    set_feedback_id_parser.add_argument(
        "--target",
        type=int,
        required=True,
        help="Target feedback ID (new MST_ID)",
    )
    add_global_args(set_feedback_id_parser)
    set_feedback_id_parser.set_defaults(func=cmd_set_feedback_id)
    
    # send-cmd-mit command
    send_cmd_mit_parser = subparsers.add_parser(
        "send-cmd-mit",
        help="Send MIT control mode command to motor",
        description="Send MIT control mode command to motor. Loops continuously until Ctrl+C.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # MIT mode with all parameters
  damiao send-cmd-mit --id 1 --position 1.5 --velocity 0.0 --stiffness 3.0 --damping 0.5

  # With custom frequency
  damiao send-cmd-mit --id 1 --position 1.5 --velocity 0.0 --stiffness 3.0 --damping 0.5 --frequency 50.0
        """
    )
    send_cmd_mit_parser.add_argument(
        "--id",
        type=int,
        required=True,
        dest="motor_id",
        help="Motor ID",
    )
    send_cmd_mit_parser.add_argument(
        "--position",
        type=float,
        required=True,
        help="Desired position (radians)",
    )
    send_cmd_mit_parser.add_argument(
        "--velocity",
        type=float,
        required=True,
        help="Desired velocity (rad/s)",
    )
    send_cmd_mit_parser.add_argument(
        "--stiffness",
        type=float,
        default=0.0,
        dest="stiffness",
        help="Stiffness (kp), range 0–500 (default: 0.0)",
    )
    send_cmd_mit_parser.add_argument(
        "--damping",
        type=float,
        default=0.0,
        dest="damping",
        help="Damping (kd), range 0–5 (default: 0.0)",
    )
    send_cmd_mit_parser.add_argument(
        "--feedforward-torque",
        type=float,
        default=0.0,
        dest="feedforward_torque",
        help="Feedforward torque (default: 0.0)",
    )
    send_cmd_mit_parser.add_argument(
        "--frequency",
        type=float,
        default=100.0,
        help="Command frequency in Hz (default: 100.0)",
    )
    add_global_args(send_cmd_mit_parser)
    send_cmd_mit_parser.set_defaults(func=cmd_send_cmd_mit)
    
    # send-cmd-pos-vel command
    send_cmd_pos_vel_parser = subparsers.add_parser(
        "send-cmd-pos-vel",
        help="Send POS_VEL control mode command to motor",
        description="Send POS_VEL control mode command to motor. Loops continuously until Ctrl+C.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # POS_VEL mode
  damiao send-cmd-pos-vel --id 1 --position 1.5 --velocity 2.0

  # With custom frequency
  damiao send-cmd-pos-vel --id 1 --position 1.5 --velocity 2.0 --frequency 50.0
        """
    )
    send_cmd_pos_vel_parser.add_argument(
        "--id",
        type=int,
        required=True,
        dest="motor_id",
        help="Motor ID",
    )
    send_cmd_pos_vel_parser.add_argument(
        "--position",
        type=float,
        required=True,
        help="Desired position (radians)",
    )
    send_cmd_pos_vel_parser.add_argument(
        "--velocity",
        type=float,
        required=True,
        help="Desired velocity (rad/s)",
    )
    send_cmd_pos_vel_parser.add_argument(
        "--frequency",
        type=float,
        default=100.0,
        help="Command frequency in Hz (default: 100.0)",
    )
    add_global_args(send_cmd_pos_vel_parser)
    send_cmd_pos_vel_parser.set_defaults(func=cmd_send_cmd_pos_vel)
    
    # send-cmd-vel command
    send_cmd_vel_parser = subparsers.add_parser(
        "send-cmd-vel",
        help="Send VEL control mode command to motor",
        description="Send VEL control mode command to motor. Loops continuously until Ctrl+C.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # VEL mode
  damiao send-cmd-vel --id 1 --velocity 3.0

  # With custom frequency
  damiao send-cmd-vel --id 1 --velocity 3.0 --frequency 50.0
        """
    )
    send_cmd_vel_parser.add_argument(
        "--id",
        type=int,
        required=True,
        dest="motor_id",
        help="Motor ID",
    )
    send_cmd_vel_parser.add_argument(
        "--velocity",
        type=float,
        required=True,
        help="Desired velocity (rad/s)",
    )
    send_cmd_vel_parser.add_argument(
        "--frequency",
        type=float,
        default=100.0,
        help="Command frequency in Hz (default: 100.0)",
    )
    add_global_args(send_cmd_vel_parser)
    send_cmd_vel_parser.set_defaults(func=cmd_send_cmd_vel)
    
    # send-cmd-force-pos command
    send_cmd_force_pos_parser = subparsers.add_parser(
        "send-cmd-force-pos",
        help="Send FORCE_POS control mode command to motor",
        description="Send FORCE_POS control mode command to motor. Loops continuously until Ctrl+C.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # FORCE_POS mode
  damiao send-cmd-force-pos --id 1 --position 1.5 --velocity-limit 50.0 --current-limit 0.8

  # With custom frequency
  damiao send-cmd-force-pos --id 1 --position 1.5 --velocity-limit 50.0 --current-limit 0.8 --frequency 50.0
        """
    )
    send_cmd_force_pos_parser.add_argument(
        "--id",
        type=int,
        required=True,
        dest="motor_id",
        help="Motor ID",
    )
    send_cmd_force_pos_parser.add_argument(
        "--position",
        type=float,
        required=True,
        help="Desired position (radians)",
    )
    send_cmd_force_pos_parser.add_argument(
        "--velocity-limit",
        type=float,
        required=True,
        dest="velocity_limit",
        help="Velocity limit (rad/s, 0-100)",
    )
    send_cmd_force_pos_parser.add_argument(
        "--current-limit",
        type=float,
        required=True,
        dest="current_limit",
        help="Torque current limit normalized (0.0-1.0)",
    )
    send_cmd_force_pos_parser.add_argument(
        "--frequency",
        type=float,
        default=100.0,
        help="Command frequency in Hz (default: 100.0)",
    )
    add_global_args(send_cmd_force_pos_parser)
    send_cmd_force_pos_parser.set_defaults(func=cmd_send_cmd_force_pos)
    
    args = parser.parse_args()
    
    # Execute the appropriate command
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    unified_main()


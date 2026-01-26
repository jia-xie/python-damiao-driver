#!/usr/bin/env python3
"""
Command handlers for CLI subcommands.
"""
import sys
import time

from damiao_motor.core.controller import DaMiaoController
from damiao_motor.gui import web_gui
from .display import (
    BOX_CORNER_TL, BOX_CORNER_TR, BOX_CORNER_BL, BOX_CORNER_BR,
    BOX_VERTICAL, BOX_HORIZONTAL, BOX_JOIN_LEFT, BOX_JOIN_RIGHT,
    GREEN, YELLOW, RESET,
    check_and_bring_up_can_interface,
    print_motor_state,
    print_warning_box,
    scan_motors,
    pad_with_ansi,
)

def cmd_scan(args) -> None:
    """
    Handle 'scan' subcommand.
    
    Scans for connected motors on the CAN bus by sending zero commands and listening for feedback.
    
    Args:
        args: Parsed command-line arguments containing:
            - channel: CAN channel (default: can0)
            - bustype: CAN bus type (default: socketcan)
            - ids: Optional list of motor IDs to test (default: 0x01-0x10)
            - duration: Duration to listen for responses in seconds (default: 0.5)
            - bitrate: CAN bitrate in bits per second (default: 1000000)
            - debug: Print all raw CAN messages for debugging (default: False)
    
    Examples:
        ```bash
        # Scan default ID range (0x01-0x10)
        damiao scan
        
        # Scan specific motor IDs
        damiao scan --ids 1 2 3
        
        # Scan with longer listen duration
        damiao scan --duration 2.0
        
        # Scan with debug output
        damiao scan --debug
        ```
    """
    # Print header and configuration in a single box
    print()
    top_border = f"{BOX_CORNER_TL}{BOX_HORIZONTAL * 78}{BOX_CORNER_TR}"
    print(top_border)
    # Header line
    header_text = f" {GREEN}DaMiao Motor Scanner{RESET}"
    print(f"{BOX_VERTICAL}{pad_with_ansi(header_text, 78)}{BOX_VERTICAL}")
    # Separator line
    print(f"{BOX_JOIN_LEFT}{BOX_HORIZONTAL * 78}{BOX_JOIN_RIGHT}")
    # Configuration lines
    config_lines = [
        f" CAN channel: {args.channel}",
        f" Bus type: {args.bustype}",
        f" Motor type: {args.motor_type} (for encoding only)",
        f" Testing motor IDs: {', '.join([hex(i) for i in args.ids]) if args.ids else '0x01-0x10 (default range)'}",
        f" Listen duration: {args.duration}s",
    ]
    if args.debug:
        config_lines.append(" Debug mode: ENABLED (printing all raw CAN messages)")
    
    for line in config_lines:
        print(f"{BOX_VERTICAL}{pad_with_ansi(line, 78)}{BOX_VERTICAL}")
    bottom_border = f"{BOX_CORNER_BL}{BOX_HORIZONTAL * 78}{BOX_CORNER_BR}"
    print(bottom_border)
    print()

    try:
        responded = scan_motors(
            channel=args.channel,
            bustype=args.bustype,
            motor_ids=args.ids,
            duration_s=args.duration,
            bitrate=args.bitrate,
            debug=args.debug,
            motor_type=args.motor_type,
        )

        # Print final summary
        print()
        if responded:
            # Combined scan summary box
            top_border = f"{BOX_CORNER_TL}{BOX_HORIZONTAL * 78}{BOX_CORNER_TR}"
            print(top_border)
            # Header line
            header_text = f" {GREEN}Scan Summary{RESET}"
            print(f"{BOX_VERTICAL}{pad_with_ansi(header_text, 78)}{BOX_VERTICAL}")
            # Separator line
            print(f"{BOX_JOIN_LEFT}{BOX_HORIZONTAL * 78}{BOX_JOIN_RIGHT}")
            # Summary lines
            summary_lines = [
                f" Found {len(responded)} motor(s):"
            ]
            for motor_id in sorted(responded):
                summary_lines.append(f"   • Motor ID: 0x{motor_id:02X} ({motor_id})")
            for line in summary_lines:
                print(f"{BOX_VERTICAL}{pad_with_ansi(line, 78)}{BOX_VERTICAL}")
            bottom_border = f"{BOX_CORNER_BL}{BOX_HORIZONTAL * 78}{BOX_CORNER_BR}"
            print(bottom_border)
        else:
            summary_lines = [
                "No motors responded.",
                "",
                "Check:",
                "  • CAN interface is up (e.g., sudo ip link set can0 up type can bitrate 1000000)",
                "  • Motors are powered and connected",
                "  • Motor IDs match the tested range",
            ]
            print_warning_box("Scan Summary - No Motors Found", summary_lines, width=80)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        raise


def cmd_set_zero(args) -> None:
    """
    Handle 'set-zero-command' subcommand.
    
    Sends a zero command to a motor continuously.
    Loops until interrupted with Ctrl+C.
    
    Args:
        args: Parsed command-line arguments containing:
            - motor_id: Motor ID to send zero command to (required)
            - frequency: Command frequency in Hz (default: 100.0)
            - channel: CAN channel (default: can0)
            - bustype: CAN bus type (default: socketcan)
            - bitrate: CAN bitrate in bits per second (default: 1000000)
    
    Examples:
        ```bash
        # Send zero command continuously
        damiao set-zero-command --id 1
        
        # With custom frequency
        damiao set-zero-command --id 1 --frequency 50.0
        ```
    """
    print("=" * 60)
    print("DaMiao Motor - Set Zero Command")
    print("=" * 60)
    print(f"CAN channel: {args.channel}")
    print(f"Motor ID: 0x{args.motor_id:02X} ({args.motor_id})")
    print("=" * 60)
    print()

    # Check and bring up CAN interface if needed
    if args.bustype == "socketcan":
        if not check_and_bring_up_can_interface(args.channel, bitrate=args.bitrate):
            print(f"⚠ Warning: Could not verify {args.channel} is ready. Continuing anyway...")

    controller = DaMiaoController(channel=args.channel, bustype=args.bustype)
    
    try:
        motor = controller.add_motor(motor_id=args.motor_id, feedback_id=0x00, motor_type=args.motor_type)
        
        # Ensure control mode is set to MIT (register 10 = 1) for zero command
        try:
            motor.ensure_control_mode("MIT")
        except Exception as e:
            print(f"⚠ Warning: Could not verify/set control mode: {e}")
            print(f"  Continuing anyway, but motor may not respond correctly.")
        
        print(f"Sending zero command continuously (press Ctrl+C to stop)...")
        print(f"  Command: pos=0, vel=0, torq=0, kp=0, kd=0")
        print(f"  Frequency: {args.frequency} Hz")
        print()
        
        interval = 1.0 / args.frequency if args.frequency > 0 else 0.01
        
        try:
            while True:
                motor.set_zero_command()
                controller.poll_feedback()
                
                if motor.state:
                    print_motor_state(motor.state)
                
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n\nStopped by user.")
        
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        print("Shutting down controller...")
        controller.shutdown()


def cmd_set_motor_id(args) -> None:
    """
    Handle 'set-motor-id' subcommand.
    
    Changes the motor's receive ID (ESC_ID, register 8). This is the ID used to send commands to the motor.
    
    Args:
        args: Parsed command-line arguments containing:
            - current: Current motor ID (to connect to the motor) (required)
            - target: Target motor ID (new receive ID) (required)
            - channel: CAN channel (default: can0)
            - bustype: CAN bus type (default: socketcan)
            - bitrate: CAN bitrate in bits per second (default: 1000000)
    
    Note:
        After changing the motor ID, you will need to use the new ID to communicate with the motor.
        The value is stored to flash memory after setting.
    
    Examples:
        ```bash
        # Change motor ID from 1 to 2
        damiao set-motor-id --current 1 --target 2
        ```
    """
    print("=" * 60)
    print("DaMiao Motor - Set Motor ID (Receive ID)")
    print("=" * 60)
    print(f"CAN channel: {args.channel}")
    print(f"Current Motor ID: 0x{args.current:02X} ({args.current})")
    print(f"Target Motor ID: 0x{args.target:02X} ({args.target})")
    print("=" * 60)
    print()

    if args.current == args.target:
        print("Current and target IDs are the same. No change needed.")
        return

    # Check and bring up CAN interface if needed
    if args.bustype == "socketcan":
        if not check_and_bring_up_can_interface(args.channel, bitrate=args.bitrate):
            print(f"⚠ Warning: Could not verify {args.channel} is ready. Continuing anyway...")

    controller = DaMiaoController(channel=args.channel, bustype=args.bustype)
    
    try:
        # Use current ID to connect
        motor = controller.add_motor(motor_id=args.current, feedback_id=0x00, motor_type=args.motor_type)
        
        print(f"Reading current register values...")
        time.sleep(0.1)
        controller.poll_feedback()
        
        # Read current receive ID (register 8)
        try:
            current_receive_id = motor.get_register(8, timeout=1.0)
            print(f"Current Receive ID (register 8): {int(current_receive_id)} (0x{int(current_receive_id):02X})")
        except Exception as e:
            print(f"⚠ Warning: Could not read register 8: {e}")
            print("  Proceeding with write anyway...")
        
        print(f"Writing new Receive ID (register 8) = {args.target} (0x{args.target:02X})...")
        motor.write_register(8, args.target)
        
        # Store parameters to flash
        print("Storing parameters to flash...")
        try:
            motor.store_parameters()
            print("✓ Parameters stored to flash")
        except Exception as e:
            print(f"⚠ Warning: Could not store parameters: {e}")
        
        print()
        print(f"✓ Motor ID changed from 0x{args.current:02X} to 0x{args.target:02X}")
        print(f"  Note: You may need to reconnect using the new ID: 0x{args.target:02X}")
        
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        controller.shutdown()


def cmd_set_zero_position(args) -> None:
    """
    Handle 'set-zero-position' subcommand.
    
    Sets the current output shaft position to zero (save position zero).
    
    Args:
        args: Parsed command-line arguments containing:
            - motor_id: Motor ID (required)
            - channel: CAN channel (default: can0)
            - bustype: CAN bus type (default: socketcan)
            - bitrate: CAN bitrate in bits per second (default: 1000000)
    
    Examples:
        ```bash
        # Set current position to zero
        damiao set-zero-position --id 1
        ```
    """
    print("=" * 60)
    print("DaMiao Motor - Set Zero Position")
    print("=" * 60)
    print(f"CAN channel: {args.channel}")
    print(f"Motor ID: 0x{args.motor_id:02X} ({args.motor_id})")
    print("=" * 60)
    print()

    # Check and bring up CAN interface if needed
    if args.bustype == "socketcan":
        if not check_and_bring_up_can_interface(args.channel, bitrate=args.bitrate):
            print(f"⚠ Warning: Could not verify {args.channel} is ready. Continuing anyway...")

    controller = DaMiaoController(channel=args.channel, bustype=args.bustype)
    
    try:
        motor = controller.add_motor(motor_id=args.motor_id, feedback_id=0x00, motor_type=args.motor_type)
        
        print(f"Setting current position to zero...")
        motor.set_zero_position()
        print(f"✓ Position zero set")
        
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        controller.shutdown()


def cmd_set_can_timeout(args) -> None:
    """
    Handle 'set-can-timeout' subcommand.
    
    Sets the CAN timeout alarm time (register 9) in milliseconds.
    
    Args:
        args: Parsed command-line arguments containing:
            - motor_id: Motor ID (required)
            - timeout_ms: Timeout in milliseconds (required)
            - channel: CAN channel (default: can0)
            - bustype: CAN bus type (default: socketcan)
            - bitrate: CAN bitrate in bits per second (default: 1000000)
    
    Note:
        Register 9 stores timeout in units of 50 microseconds: **1 register unit = 50 microseconds**.
        
        The timeout is internally converted from milliseconds to register units using:
        register_value = timeout_ms × 20
        
        Examples:
        - 1000 ms = 20,000 register units
        - 50 ms = 1,000 register units
        
        The value is stored to flash memory after setting.
    
    Examples:
        ```bash
        # Set CAN timeout to 1000 ms
        damiao set-can-timeout --id 1 --timeout 1000
        ```
    """
    print("=" * 60)
    print("DaMiao Motor - Set CAN Timeout")
    print("=" * 60)
    print(f"CAN channel: {args.channel}")
    print(f"Motor ID: 0x{args.motor_id:02X} ({args.motor_id})")
    print(f"Timeout: {args.timeout_ms} ms")
    print("=" * 60)
    print()

    # Check and bring up CAN interface if needed
    if args.bustype == "socketcan":
        if not check_and_bring_up_can_interface(args.channel, bitrate=args.bitrate):
            print(f"⚠ Warning: Could not verify {args.channel} is ready. Continuing anyway...")

    controller = DaMiaoController(channel=args.channel, bustype=args.bustype)
    
    try:
        motor = controller.add_motor(motor_id=args.motor_id, feedback_id=0x00, motor_type=args.motor_type)
        
        print(f"Setting CAN timeout to {args.timeout_ms} ms (register 9)...")
        motor.set_can_timeout(args.timeout_ms)
        
        # Store parameters to flash
        print("Storing parameters to flash...")
        try:
            motor.store_parameters()
            print("✓ Parameters stored to flash")
        except Exception as e:
            print(f"⚠ Warning: Could not store parameters: {e}")
        
        print()
        print(f"✓ CAN timeout set to {args.timeout_ms} ms")
        
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        controller.shutdown()


def cmd_send_cmd_mit(args) -> None:
    """
    Handle 'send-cmd-mit' subcommand.
    
    Sends MIT control mode command to motor. Loops continuously until Ctrl+C.
    
    Args:
        args: Parsed command-line arguments containing:
            - motor_id: Motor ID (required)
            - position: Desired position (radians) (required)
            - velocity: Desired velocity (rad/s) (required)
            - stiffness: Stiffness (kp) (default: 0.0)
            - damping: Damping (kd) (default: 0.0)
            - feedforward_torque: Feedforward torque (default: 0.0)
            - frequency: Command frequency in Hz (default: 100.0)
            - channel: CAN channel (default: can0)
            - bustype: CAN bus type (default: socketcan)
            - bitrate: CAN bitrate in bits per second (default: 1000000)
    
    Examples:
        ```bash
        damiao send-cmd-mit --id 1 --position 1.5 --velocity 0.0 --stiffness 3.0 --damping 0.5
        ```
    """
    print("=" * 60)
    print("DaMiao Motor - Send MIT Command")
    print("=" * 60)
    print(f"CAN channel: {args.channel}")
    print(f"Motor ID: 0x{args.motor_id:02X} ({args.motor_id})")
    print(f"Control Mode: MIT")
    print(f"  Position: {args.position:.6f} rad")
    print(f"  Velocity: {args.velocity:.6f} rad/s")
    print(f"  Stiffness (kp): {args.stiffness:.6f}")
    print(f"  Damping (kd): {args.damping:.6f}")
    print(f"  Feedforward Torque: {args.feedforward_torque:.6f} Nm")
    print(f"Frequency: {args.frequency} Hz")
    print("=" * 60)
    print()

    # Check and bring up CAN interface if needed
    if args.bustype == "socketcan":
        if not check_and_bring_up_can_interface(args.channel, bitrate=args.bitrate):
            print(f"⚠ Warning: Could not verify {args.channel} is ready. Continuing anyway...")

    controller = DaMiaoController(channel=args.channel, bustype=args.bustype)
    
    try:
        motor = controller.add_motor(motor_id=args.motor_id, feedback_id=0x00, motor_type=args.motor_type)
        motor.ensure_control_mode("MIT")
        
        print(f"Sending MIT command continuously (press Ctrl+C to stop)...")
        print(f"  CAN ID: 0x{args.motor_id:03X}")
        print(f"  Frequency: {args.frequency} Hz")
        print()
        
        interval = 1.0 / args.frequency if args.frequency > 0 else 0.01
        
        try:
            while True:
                motor.send_cmd_mit(
                    target_position=args.position,
                    target_velocity=args.velocity,
                    stiffness=args.stiffness,
                    damping=args.damping,
                    feedforward_torque=args.feedforward_torque,
                )
                controller.poll_feedback()
                
                if motor.state:
                    print_motor_state(motor.state)
                
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n\nStopped by user.")
        
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        print("Shutting down controller...")
        controller.shutdown()


def cmd_send_cmd_pos_vel(args) -> None:
    """
    Handle 'send-cmd-pos-vel' subcommand.
    
    Sends POS_VEL control mode command to motor. Loops continuously until Ctrl+C.
    
    Args:
        args: Parsed command-line arguments containing:
            - motor_id: Motor ID (required)
            - position: Desired position (radians) (required)
            - velocity: Desired velocity (rad/s) (required)
            - frequency: Command frequency in Hz (default: 100.0)
            - channel: CAN channel (default: can0)
            - bustype: CAN bus type (default: socketcan)
            - bitrate: CAN bitrate in bits per second (default: 1000000)
    
    Examples:
        ```bash
        damiao send-cmd-pos-vel --id 1 --position 1.5 --velocity 2.0
        ```
    """
    print("=" * 60)
    print("DaMiao Motor - Send POS_VEL Command")
    print("=" * 60)
    print(f"CAN channel: {args.channel}")
    print(f"Motor ID: 0x{args.motor_id:02X} ({args.motor_id})")
    print(f"Control Mode: POS_VEL")
    print(f"  Position: {args.position:.6f} rad")
    print(f"  Velocity: {args.velocity:.6f} rad/s")
    print(f"Frequency: {args.frequency} Hz")
    print("=" * 60)
    print()

    # Check and bring up CAN interface if needed
    if args.bustype == "socketcan":
        if not check_and_bring_up_can_interface(args.channel, bitrate=args.bitrate):
            print(f"⚠ Warning: Could not verify {args.channel} is ready. Continuing anyway...")

    controller = DaMiaoController(channel=args.channel, bustype=args.bustype)
    
    try:
        motor = controller.add_motor(motor_id=args.motor_id, feedback_id=0x00, motor_type=args.motor_type)
        motor.ensure_control_mode("POS_VEL")
        
        print(f"Sending POS_VEL command continuously (press Ctrl+C to stop)...")
        print(f"  CAN ID: 0x{0x100 + args.motor_id:03X}")
        print(f"  Frequency: {args.frequency} Hz")
        print()
        
        interval = 1.0 / args.frequency if args.frequency > 0 else 0.01
        
        try:
            while True:
                motor.send_cmd_pos_vel(
                    target_position=args.position,
                    target_velocity=args.velocity,
                )
                controller.poll_feedback()
                
                if motor.state:
                    print_motor_state(motor.state)
                
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n\nStopped by user.")
        
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        print("Shutting down controller...")
        controller.shutdown()


def cmd_send_cmd_vel(args) -> None:
    """
    Handle 'send-cmd-vel' subcommand.
    
    Sends VEL control mode command to motor. Loops continuously until Ctrl+C.
    
    Args:
        args: Parsed command-line arguments containing:
            - motor_id: Motor ID (required)
            - velocity: Desired velocity (rad/s) (required)
            - frequency: Command frequency in Hz (default: 100.0)
            - channel: CAN channel (default: can0)
            - bustype: CAN bus type (default: socketcan)
            - bitrate: CAN bitrate in bits per second (default: 1000000)
    
    Examples:
        ```bash
        damiao send-cmd-vel --id 1 --velocity 3.0
        ```
    """
    print("=" * 60)
    print("DaMiao Motor - Send VEL Command")
    print("=" * 60)
    print(f"CAN channel: {args.channel}")
    print(f"Motor ID: 0x{args.motor_id:02X} ({args.motor_id})")
    print(f"Control Mode: VEL")
    print(f"  Velocity: {args.velocity:.6f} rad/s")
    print(f"Frequency: {args.frequency} Hz")
    print("=" * 60)
    print()

    # Check and bring up CAN interface if needed
    if args.bustype == "socketcan":
        if not check_and_bring_up_can_interface(args.channel, bitrate=args.bitrate):
            print(f"⚠ Warning: Could not verify {args.channel} is ready. Continuing anyway...")

    controller = DaMiaoController(channel=args.channel, bustype=args.bustype)
    
    try:
        motor = controller.add_motor(motor_id=args.motor_id, feedback_id=0x00, motor_type=args.motor_type)
        motor.ensure_control_mode("VEL")
        
        print(f"Sending VEL command continuously (press Ctrl+C to stop)...")
        print(f"  CAN ID: 0x{0x200 + args.motor_id:03X}")
        print(f"  Frequency: {args.frequency} Hz")
        print()
        
        interval = 1.0 / args.frequency if args.frequency > 0 else 0.01
        
        try:
            while True:
                motor.send_cmd_vel(
                    target_velocity=args.velocity,
                )
                controller.poll_feedback()
                
                if motor.state:
                    print_motor_state(motor.state)
                
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n\nStopped by user.")
        
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        print("Shutting down controller...")
        controller.shutdown()


def cmd_send_cmd_force_pos(args) -> None:
    """
    Handle 'send-cmd-force-pos' subcommand.
    
    Sends FORCE_POS control mode command to motor. Loops continuously until Ctrl+C.
    
    Args:
        args: Parsed command-line arguments containing:
            - motor_id: Motor ID (required)
            - position: Desired position (radians) (required)
            - velocity_limit: Velocity limit (rad/s, 0-100) (required)
            - current_limit: Torque current limit normalized (0.0-1.0) (required)
            - frequency: Command frequency in Hz (default: 100.0)
            - channel: CAN channel (default: can0)
            - bustype: CAN bus type (default: socketcan)
            - bitrate: CAN bitrate in bits per second (default: 1000000)
    
    Examples:
        ```bash
        damiao send-cmd-force-pos --id 1 --position 1.5 --velocity-limit 50.0 --current-limit 0.8
        ```
    """
    print("=" * 60)
    print("DaMiao Motor - Send FORCE_POS Command")
    print("=" * 60)
    print(f"CAN channel: {args.channel}")
    print(f"Motor ID: 0x{args.motor_id:02X} ({args.motor_id})")
    print(f"Control Mode: FORCE_POS")
    print(f"  Position: {args.position:.6f} rad")
    print(f"  Velocity Limit: {args.velocity_limit:.6f} rad/s")
    print(f"  Current Limit: {args.current_limit:.6f}")
    print(f"Frequency: {args.frequency} Hz")
    print("=" * 60)
    print()

    # Check and bring up CAN interface if needed
    if args.bustype == "socketcan":
        if not check_and_bring_up_can_interface(args.channel, bitrate=args.bitrate):
            print(f"⚠ Warning: Could not verify {args.channel} is ready. Continuing anyway...")

    controller = DaMiaoController(channel=args.channel, bustype=args.bustype)
    
    try:
        motor = controller.add_motor(motor_id=args.motor_id, feedback_id=0x00, motor_type=args.motor_type)
        motor.ensure_control_mode("FORCE_POS")
        
        print(f"Sending FORCE_POS command continuously (press Ctrl+C to stop)...")
        print(f"  CAN ID: 0x{0x300 + args.motor_id:03X}")
        print(f"  Frequency: {args.frequency} Hz")
        print()
        
        interval = 1.0 / args.frequency if args.frequency > 0 else 0.01
        
        try:
            while True:
                motor.send_cmd_force_pos(
                    target_position=args.position,
                    velocity_limit=args.velocity_limit,
                    current_limit=args.current_limit,
                )
                controller.poll_feedback()
                
                if motor.state:
                    print_motor_state(motor.state)
                
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n\nStopped by user.")
        
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        print("Shutting down controller...")
        controller.shutdown()


def cmd_gui(args) -> None:
    """
    Handle 'gui' subcommand.
    
    Launches the web-based GUI for viewing and controlling DaMiao motors.
    
    Args:
        args: Parsed command-line arguments containing:
            - host: Host to bind to (default: 127.0.0.1)
            - port: Port to bind to (default: 5000)
            - debug: Enable debug mode (default: False)
            - production: Use production WSGI server (default: False)
    
    Examples:
        ```bash
        # Start GUI on default host and port
        damiao gui
        
        # Start GUI on custom port
        damiao gui --port 8080
        
        # Start GUI on all interfaces
        damiao gui --host 0.0.0.0
        
        # Start GUI with production server
        damiao gui --production
        ```
    """
    web_gui.run_server(
        host=args.host,
        port=args.port,
        debug=args.debug,
        production=args.production
    )


def cmd_set_feedback_id(args) -> None:
    """
    Handle 'set-feedback-id' subcommand.
    
    Changes the motor's feedback ID (MST_ID, register 7). This is the ID used to identify feedback messages from the motor.
    
    Args:
        args: Parsed command-line arguments containing:
            - current: Current motor ID (to connect to the motor) (required)
            - target: Target feedback ID (new MST_ID) (required)
            - channel: CAN channel (default: can0)
            - bustype: CAN bus type (default: socketcan)
            - bitrate: CAN bitrate in bits per second (default: 1000000)
    
    Note:
        The motor will now respond with feedback using the new feedback ID.
        The value is stored to flash memory after setting.
    
    Examples:
        ```bash
        # Change feedback ID to 3 (using motor ID 1 to connect)
        damiao set-feedback-id --current 1 --target 3
        ```
    """
    print("=" * 60)
    print("DaMiao Motor - Set Feedback ID (MST_ID)")
    print("=" * 60)
    print(f"CAN channel: {args.channel}")
    print(f"Current Motor ID: 0x{args.current:02X} ({args.current})")
    print(f"Target Feedback ID: 0x{args.target:02X} ({args.target})")
    print("=" * 60)
    print()

    # Check and bring up CAN interface if needed
    if args.bustype == "socketcan":
        if not check_and_bring_up_can_interface(args.channel, bitrate=args.bitrate):
            print(f"⚠ Warning: Could not verify {args.channel} is ready. Continuing anyway...")

    controller = DaMiaoController(channel=args.channel, bustype=args.bustype)
    
    try:
        # Use current motor ID to connect
        motor = controller.add_motor(motor_id=args.current, feedback_id=0x00, motor_type=args.motor_type)
        
        print(f"Reading current register values...")
        time.sleep(0.1)
        controller.poll_feedback()
        
        # Read current feedback ID (register 7)
        try:
            current_feedback_id = motor.get_register(7, timeout=1.0)
            print(f"Current Feedback ID (register 7): {int(current_feedback_id)} (0x{int(current_feedback_id):02X})")
        except Exception as e:
            print(f"⚠ Warning: Could not read register 7: {e}")
            print("  Proceeding with write anyway...")
        
        print(f"Writing new Feedback ID (register 7) = {args.target} (0x{args.target:02X})...")
        motor.write_register(7, args.target)
        
        # Store parameters to flash
        print("Storing parameters to flash...")
        try:
            motor.store_parameters()
            print("✓ Parameters stored to flash")
        except Exception as e:
            print(f"⚠ Warning: Could not store parameters: {e}")
        
        print()
        print(f"✓ Feedback ID changed to 0x{args.target:02X}")
        print(f"  Note: Motor will now respond with feedback ID 0x{args.target:02X}")
        
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        controller.shutdown()


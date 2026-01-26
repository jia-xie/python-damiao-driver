import argparse
import time
import math

from damiao_motor import DaMiaoController


def main() -> None:
    """
    WARNING: This example will move the motor.
    Make sure the motor is mounted and operated in a safe condition
    (no loose clothing, secure the mechanism, keep clear of moving parts).

    Single-motor demo using the package API.
    """
    parser = argparse.ArgumentParser(
        description="Single motor control example",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default motor ID 0x01 with feedback ID 0x00
  python examples/single_motor.py

  # Specify motor ID and feedback ID
  python examples/single_motor.py --motor-id 0x02 --feedback-id 0x01

  # Use decimal values
  python examples/single_motor.py --motor-id 3 --feedback-id 1
        """
    )
    parser.add_argument(
        '--motor-id',
        type=lambda x: int(x, 0),  # Supports hex (0x01) and decimal (1)
        default=0x01,
        help='Motor ID (command/receive ID) in hex (0x01) or decimal (1). Default: 0x01'
    )
    parser.add_argument(
        '--feedback-id',
        type=lambda x: int(x, 0),  # Supports hex (0x00) and decimal (0)
        default=0x00,
        help='Feedback ID (MST_ID) in hex (0x00) or decimal (0). Default: 0x00'
    )
    parser.add_argument(
        '--channel',
        type=str,
        default='can0',
        help='CAN channel (default: can0)'
    )
    parser.add_argument(
        '--motor-type',
        type=str,
        default='DM4340',
        help='Motor type for P/V/T presets (default: DM4340)'
    )
    parser.add_argument(
        '--no-confirm',
        action='store_true',
        help='Skip safety confirmation prompt'
    )
    args = parser.parse_args()

    if not args.no_confirm:
        confirm = input(
            "WARNING: This example will MOVE the motor.\n"
            "Ensure it is mounted and operated safely (no loose clothing, secure mechanism, clear of moving parts).\n"
            "Type 'yes' to continue: "
        ).strip().lower()
        if confirm != "yes":
            print("Aborting: user did not confirm safety.")
            return

    print(f"Connecting to motor ID 0x{args.motor_id:02X} (feedback ID 0x{args.feedback_id:02X}) on {args.channel}")

    controller = DaMiaoController(channel=args.channel, bustype="socketcan")
    motor = controller.add_motor(motor_id=args.motor_id, feedback_id=args.feedback_id, motor_type=args.motor_type)

    controller.enable_all()
    time.sleep(0.1)

    kp = 20.0
    kd = 0.5

    # Control loop
    freq_hz = 100.0
    period = 1.0 / freq_hz
    next_send_time = time.perf_counter()
    
    try:
        while True:
            now = time.perf_counter()
            
            # Send commands at fixed frequency
            if now >= next_send_time:
                t = now
                target_pos = 1.0 * math.sin(2.0 * math.pi * 0.2 * t)
                motor.send_cmd(target_position=target_pos, target_velocity=0.0, stiffness=kp, damping=kd, feedforward_torque=0.0)
                
                # Print feedback
                states = motor.get_states()
                if states:
                    print(f"ID 0x{motor.motor_id:02X}: {states}")
                
                next_send_time += period
                if now > next_send_time:
                    next_send_time = now + period
            
            time.sleep(0.0001)
    except KeyboardInterrupt:
        controller.shutdown()


if __name__ == "__main__":
    main()



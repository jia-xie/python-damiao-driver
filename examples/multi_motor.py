import argparse
import math
import time

from damiao_motor import DaMiaoController


def main() -> None:
    """
    WARNING: This example will move multiple motors.
    Make sure all motors are mounted and operated in safe conditions
    (no loose clothing, secure the mechanism, keep clear of moving parts).

    Multi-motor demo with configurable motor IDs.
    """
    parser = argparse.ArgumentParser(
        description="Multi-motor control example",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default motors (0x01 and 0x02) with feedback ID 0x00
  python examples/multi_motor.py

  # Specify motor IDs
  python examples/multi_motor.py --motor-ids 0x01 0x02 0x03

  # Specify motor IDs and feedback IDs (must match number of motor IDs)
  python examples/multi_motor.py --motor-ids 0x01 0x02 --feedback-ids 0x00 0x01

  # Use decimal values
  python examples/multi_motor.py --motor-ids 1 2 3
        """
    )
    parser.add_argument(
        '--motor-ids',
        type=lambda x: int(x, 0),  # Supports hex (0x01) and decimal (1)
        nargs='+',
        default=[0x01, 0x02],
        help='Motor IDs (command/receive IDs) in hex (0x01) or decimal (1). Default: 0x01 0x02'
    )
    parser.add_argument(
        '--feedback-ids',
        type=lambda x: int(x, 0),  # Supports hex (0x00) and decimal (0)
        nargs='+',
        default=None,
        help='Feedback IDs (MST_IDs). If not specified, uses 0x00 for all motors. Must match number of motor IDs if specified.'
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

    # Validate feedback IDs
    if args.feedback_ids is None:
        feedback_ids = [0x00] * len(args.motor_ids)
    else:
        if len(args.feedback_ids) != len(args.motor_ids):
            parser.error(f"Number of feedback IDs ({len(args.feedback_ids)}) must match number of motor IDs ({len(args.motor_ids)})")
        feedback_ids = args.feedback_ids

    if not args.no_confirm:
        confirm = input(
            "WARNING: This example will MOVE MULTIPLE motors.\n"
            "Ensure all are mounted and operated safely (no loose clothing, secure mechanism, clear of moving parts).\n"
            "Type 'yes' to continue: "
        ).strip().lower()
        if confirm != "yes":
            print("Aborting: user did not confirm safety.")
            return

    print(f"Connecting to {len(args.motor_ids)} motor(s) on {args.channel}:")
    for i, (motor_id, feedback_id) in enumerate(zip(args.motor_ids, feedback_ids), 1):
        print(f"  Motor {i}: ID 0x{motor_id:02X} (feedback ID 0x{feedback_id:02X})")

    controller = DaMiaoController(channel=args.channel, bustype="socketcan")

    for motor_id, feedback_id in zip(args.motor_ids, feedback_ids):
        controller.add_motor(motor_id=motor_id, feedback_id=feedback_id, motor_type=args.motor_type)

    controller.enable_all()
    time.sleep(0.1)

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
                kp = 20.0
                kd = 0.5
                for motor in controller.all_motors():
                    motor.send_cmd(target_position=target_pos, target_velocity=0.0, stiffness=kp, damping=kd, feedforward_torque=0.0)
                
                # Print feedback for all motors
                for motor in controller.all_motors():
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



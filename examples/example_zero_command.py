"""Send zero MIT command to motor ID 0x01. Prints feedback. Ctrl+C to stop."""

import sys
import time

from damiao_motor import DaMiaoController

if sys.platform == "darwin":
    controller = DaMiaoController(channel=0, bustype="gs_usb", bitrate=1000000)
else:
    controller = DaMiaoController(channel="can0", bustype="socketcan")

motor = controller.add_motor(motor_id=0x07, feedback_id=0x17, motor_type="4310")

try:
    while True:
        motor.send_cmd_mit(
            target_position=0.0,
            target_velocity=0.0,
            stiffness=0.0,
            damping=0.0,
            feedforward_torque=0.0,
        )
        controller.poll_feedback()
        if motor.state:
            print(
                f"Pos:{motor.state.get('pos', 0.0):8.3f} rad | "
                f"Vel:{motor.state.get('vel', 0.0):8.3f} rad/s | "
                f"Torq:{motor.state.get('torq', 0.0):8.3f} Nm"
            )
        time.sleep(0.01)
except KeyboardInterrupt:
    print("\nStopped.")
finally:
    controller.shutdown()

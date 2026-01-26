"""Minimal DaMiao motor example. Sends a slow sine to position. Ctrl+C to stop."""
import math
import time

from damiao_motor import DaMiaoController

controller = DaMiaoController(channel="can0", bustype="socketcan")
motor = controller.add_motor(motor_id=0x01, feedback_id=0x11, motor_type="4310")
# Available motor types: 3507, 4310, 4340, 6006, 8006, 8009, 10010L,
# 10010, H3510, G6215, H6220, JH11, 6248P


controller.enable_all()
time.sleep(0.1)
motor.ensure_control_mode("MIT") # Available modes: MIT, POS_VEL, VEL, FORCE_POS

try:
    while True:
        motor.send_cmd_mit(
            target_position=math.sin(0.2 * time.time()),
            target_velocity=0.0,
            stiffness=1.0,
            damping=0.5,
            feedforward_torque=0.0,
        )
        states = motor.get_states()
        if states:
            print(states)
        time.sleep(0.1)
except KeyboardInterrupt:
    pass

controller.shutdown()

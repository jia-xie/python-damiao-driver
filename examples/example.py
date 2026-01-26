"""Minimal DaMiao motor example. Sends a slow sine to position. Ctrl+C to stop."""
import math
import time

from damiao_motor import DaMiaoController

controller = DaMiaoController(channel="can0", bustype="socketcan")
motor = controller.add_motor(motor_id=0x01, feedback_id=0x11, motor_type="DM4310") 
# Available motor types: DM3507, DM4310, DM4340, DM6006, DM8006, DM8009, DM10010L, 
# DM10010, DMH3510, DMG6215, DMH6220, DMJH11, DM6248P


controller.enable_all()
time.sleep(0.1)
motor.ensure_control_mode("MIT") # Available modes: MIT, POS_VEL, VEL, FORCE_POS

try:
    while True:
        motor.send_cmd(
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

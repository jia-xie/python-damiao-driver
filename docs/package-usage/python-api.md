---
tags:
  - usage
  - python
  - api
---

# Python API Guide

Use the Python API when you want to script repeatable workflows, integrate with your own control loop, or build higher-level application logic.

## Quick Start

```python
import time

from damiao_motor import DaMiaoController

controller = DaMiaoController(channel="can0", bustype="socketcan")
motor = controller.add_motor(motor_id=0x01, feedback_id=0x00, motor_type="4340")

motor.enable()
motor.ensure_control_mode("MIT")
motor.send_cmd_mit(
    target_position=0.0,
    target_velocity=0.0,
    stiffness=3.0,
    damping=0.5,
    feedforward_torque=0.0,
)

time.sleep(0.05)  # allow background polling to receive feedback
print(motor.get_states())

motor.disable()
controller.shutdown()
```

## Typical Workflow

1. Create a [`DaMiaoController`](../api/controller.md#damiao_motor.core.controller.DaMiaoController).
2. Add one or more motors with [`add_motor(...)`](../api/controller.md#damiao_motor.core.controller.DaMiaoController.add_motor).
3. Enable motor(s) and call [`ensure_control_mode(...)`](../api/motor.md#damiao_motor.core.motor.DaMiaoMotor.ensure_control_mode) for the intended command mode.
4. Send one mode-specific command:

    - MIT mode: [`send_cmd_mit(...)`](../api/motor.md#damiao_motor.core.motor.DaMiaoMotor.send_cmd_mit)
    - POS_VEL mode: [`send_cmd_pos_vel(...)`](../api/motor.md#damiao_motor.core.motor.DaMiaoMotor.send_cmd_pos_vel)
    - VEL mode: [`send_cmd_vel(...)`](../api/motor.md#damiao_motor.core.motor.DaMiaoMotor.send_cmd_vel)
    - FORCE_POS mode: [`send_cmd_force_pos(...)`](../api/motor.md#damiao_motor.core.motor.DaMiaoMotor.send_cmd_force_pos)

5. Read the latest state with [`get_states()`](../api/motor.md#damiao_motor.core.motor.DaMiaoMotor.get_states).

    - These states are polled automatically by the controller in background after [`add_motor(...)`](../api/controller.md#damiao_motor.core.controller.DaMiaoController.add_motor).

6. Disable motors and call [`shutdown()`](../api/controller.md#damiao_motor.core.controller.DaMiaoController.shutdown).

## Feedback Handling Routine

When a motor is added to [`DaMiaoController`](../api/controller.md#damiao_motor.core.controller.DaMiaoController), feedback handling is automatic.

1. [`add_motor(...)`](../api/controller.md#damiao_motor.core.controller.DaMiaoController.add_motor) registers the motor and starts background polling.
2. The controller thread repeatedly calls [`poll_feedback()`](../api/controller.md#damiao_motor.core.controller.DaMiaoController.poll_feedback).
3. `poll_feedback()` drains pending frames with non-blocking `recv(timeout=0)`, extracts logical ID from `D[0]`, and dispatches frames to [`process_feedback_frame(...)`](../api/motor.md#damiao_motor.core.motor.DaMiaoMotor.process_feedback_frame).
4. The motor decoder updates runtime state (`status`, `pos`, `vel`, `torq`, `t_mos`, `t_rotor`) and processes register replies if present.
5. Your code reads a snapshot via [`get_states()`](../api/motor.md#damiao_motor.core.motor.DaMiaoMotor.get_states).

In normal use you do not need to call `poll_feedback()` manually.  
Call [`shutdown()`](../api/controller.md#damiao_motor.core.controller.DaMiaoController.shutdown) before exit to stop the polling thread cleanly.

## Register Write vs Store

- **Write**: update runtime register values in RAM with [`write_register(...)`](../api/motor.md#damiao_motor.core.motor.DaMiaoMotor.write_register).
- **Store**: persist runtime values to flash with [`store_parameters()`](../api/motor.md#damiao_motor.core.motor.DaMiaoMotor.store_parameters).

For semantics and register list, see [Registers](../concept/registers.md).

## Reference

- [DaMiaoController API](../api/controller.md)
- [DaMiaoMotor API](../api/motor.md)
- [Motor Control Modes](../concept/motor-control-modes.md)
- [Communication Protocol](../concept/communication-protocol.md)

# Quick Start

This guide will help you get started with controlling DaMiao motors in just a few minutes.

## Prerequisites

- DaMiao motor connected to a CAN bus
- CAN interface configured (see [CAN Setup](../configuration/can-setup.md))
- Python 3.8+ installed

## Basic Example

Here's a minimal example to get you started:

```python
import time
import math
from damiao_motor import DaMiaoController

# Create controller and connect to CAN bus
controller = DaMiaoController(channel="can0", bustype="socketcan")

# Add a motor (ID 0x01, feedback ID 0x00)
motor = controller.add_motor(motor_id=0x01, feedback_id=0x00)

# Enable the motor
controller.enable_all()
time.sleep(0.1)  # Wait for motor to enable

# Control loop
try:
    while True:
        # Send sinusoidal position command
        target_pos = 1.0 * math.sin(2.0 * math.pi * 0.2 * time.time())
        motor.send_cmd(
            target_position=target_pos,
            target_velocity=0.0,
            stiffness=20.0,
            damping=0.5,
            feedforward_torque=0.0
        )
        
        # Read feedback
        states = motor.get_states()
        if states:
            print(f"Position: {states.get('pos'):.3f}, "
                  f"Velocity: {states.get('vel'):.3f}")
        
        time.sleep(0.01)
except KeyboardInterrupt:
    controller.shutdown()
```

## What's Happening?

1. **Controller Creation**: `DaMiaoController` manages the CAN bus connection
2. **Motor Addition**: `add_motor()` registers a motor with its ID
3. **Enable**: `enable_all()` enables all motors for control
4. **Control Loop**: `send_cmd()` sends position/velocity commands
5. **Feedback**: `get_states()` retrieves current motor state
6. **Cleanup**: `shutdown()` properly closes connections

## Command Parameters

The `send_cmd()` method accepts:

- `target_position` - Desired position (radians)
- `target_velocity` - Desired velocity (rad/s)
- `stiffness` - Position gain (kp)
- `damping` - Velocity gain (kd)
- `feedforward_torque` - Feedforward torque (Nm)

## Next Steps

- [API Reference](../api/controller.md) - Complete API documentation
- [Motor Configuration](../configuration/motor-config.md) - Configure motor parameters


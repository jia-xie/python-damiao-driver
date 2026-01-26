---
tags:
  - concept
  - control-modes
  - reference
---

# Motor Control Modes

DaMiao motors support four different control modes, each optimized for different use cases.

## Overview

Control modes determine how the motor interprets command messages. The control mode is set via register 10 (CTRL_MODE) and must match the command format being sent.

| Mode | Register Value | CAN ID Format | Use Case |
|------|---------------|---------------|----------|
| MIT | 1 | `motor_id` | Impedance control with stiffness/damping |
| POS_VEL | 2 | `0x100 + motor_id` | Trapezoidal motion profiles |
| VEL | 3 | `0x200 + motor_id` | Velocity control |
| FORCE_POS | 4 | `0x300 + motor_id` | Position control with limits |

## MIT Mode

**MIT mode** (named after MIT's Cheetah robot) provides impedance control with position, velocity, stiffness, damping, and feedforward torque.

### Characteristics

- **Full impedance control**: Adjustable stiffness and damping
- **Feedforward torque**: Direct torque control for compensation
- **Flexible**: Suitable for compliant manipulation and force control
- **Most parameters**: Requires tuning of kp (stiffness) and kd (damping)

### Command Parameters

| Parameter | Range | Description |
|-----------|-------|-------------|
| `target_position` | Motor-specific | Desired position (radians) |
| `target_velocity` | Motor-specific | Desired velocity (rad/s) |
| `stiffness` (kp) | 0-500 | Position gain (stiffness) |
| `damping` (kd) | 0-5 | Velocity gain (damping) |
| `feedforward_torque` | Motor-specific | Feedforward torque (Nm) |

### Control Law

The motor implements an impedance controller:

```
τ = kp * (θ_target - θ_actual) + kd * (ω_target - ω_actual) + τ_ff
```

Where:
- `τ` is the output torque
- `kp` is stiffness (position gain)
- `kd` is damping (velocity gain)
- `θ` is position
- `ω` is velocity
- `τ_ff` is feedforward torque

### Use Cases

- **Compliant manipulation**: Soft interactions with environment
- **Force control**: Precise force application
- **Impedance matching**: Match desired mechanical impedance
- **Research applications**: Flexible control for experiments

### Example

```python
motor.ensure_control_mode("MIT")
motor.send_cmd_mit(
    target_position=1.0,      # 1 radian
    target_velocity=0.0,      # Hold position
    stiffness=20.0,           # Moderate stiffness
    damping=0.5,              # Moderate damping
    feedforward_torque=0.0    # No feedforward
)
```

## POS_VEL Mode

**POS_VEL mode** provides position-velocity control for trapezoidal motion profiles.

### Characteristics

- **Trapezoidal profiles**: Built-in acceleration/deceleration
- **Position + velocity**: Target position with maximum velocity
- **Simpler**: Fewer parameters than MIT mode
- **Smooth motion**: Automatic trajectory generation

### Command Parameters

| Parameter | Range | Description |
|-----------|-------|-------------|
| `target_position` | Motor-specific | Desired position (radians) |
| `target_velocity` | Motor-specific | Maximum velocity during motion (rad/s) |

### Behavior

The motor moves toward the target position, limiting velocity to the specified maximum. The motor firmware handles acceleration and deceleration automatically.

### Use Cases

- **Point-to-point motion**: Moving to specific positions
- **Trajectory following**: Following predefined paths
- **Simple control**: When impedance control is not needed

### Example

```python
motor.ensure_control_mode("POS_VEL")
motor.send_cmd_pos_vel(
    target_position=2.0,      # Target: 2 radians
    target_velocity=3.0       # Max velocity: 3 rad/s
)
```

## VEL Mode

**VEL mode** provides pure velocity control.

### Characteristics

- **Velocity control**: Direct velocity command
- **Simplest**: Single parameter
- **Continuous motion**: For constant-speed applications
- **No position target**: Motor maintains commanded velocity

### Command Parameters

| Parameter | Range | Description |
|-----------|-------|-------------|
| `target_velocity` | Motor-specific | Desired velocity (rad/s) |

### Behavior

The motor maintains the commanded velocity. Positive values rotate in one direction, negative values in the opposite direction.

### Use Cases

- **Constant speed**: Maintaining steady rotation
- **Velocity following**: Following velocity profiles
- **Simple applications**: When position control is not needed

### Example

```python
motor.ensure_control_mode("VEL")
motor.send_cmd_vel(
    target_velocity=2.0       # Rotate at 2 rad/s
)
```

## FORCE_POS Mode

**FORCE_POS mode** (Force-Position Hybrid) provides position control with velocity and current limits.

### Characteristics

- **Position control**: Moves to target position
- **Safety limits**: Velocity and current limits for safety
- **Hybrid approach**: Combines position and force control
- **Safe operation**: Limits prevent excessive forces

### Command Parameters

| Parameter | Range | Description |
|-----------|-------|-------------|
| `target_position` | Motor-specific | Desired position (radians) |
| `velocity_limit` | 0-100 rad/s | Maximum velocity during motion |
| `current_limit` | 0.0-1.0 | Torque current limit (normalized) |

### Behavior

The motor moves toward the target position while respecting the velocity and current limits. This provides safe position control with force limiting.

### Use Cases

- **Safe positioning**: When force limits are critical
- **Obstacle avoidance**: Limiting force when encountering obstacles
- **Human-robot interaction**: Safe operation near humans
- **Constrained environments**: Operating in tight spaces

### Example

```python
motor.ensure_control_mode("FORCE_POS")
motor.send_cmd_force_pos(
    target_position=1.5,          # Target: 1.5 radians
    velocity_limit=50.0,          # Max velocity: 50 rad/s
    current_limit=0.8             # Max current: 80% of rated
)
```

## Mode Selection Guide

### Choose MIT Mode When:

- You need compliant/impedance control
- Force control is required
- Research or experimental applications
- You want full control over stiffness/damping

### Choose POS_VEL Mode When:

- You need smooth point-to-point motion
- Trapezoidal profiles are sufficient
- Simpler control is acceptable
- Position accuracy is important

### Choose VEL Mode When:

- You only need velocity control
- Position is not important
- Constant-speed operation
- Simplest possible control

### Choose FORCE_POS Mode When:

- Safety is critical
- Force limits are required
- Operating in constrained environments
- Human-robot interaction

## Switching Between Modes

The control mode must be set before sending commands:

```python
# Switch to MIT mode
motor.ensure_control_mode("MIT")
motor.send_cmd_mit(...)  # MIT commands

# Switch to VEL mode
motor.ensure_control_mode("VEL")
motor.send_cmd_vel(...)  # VEL commands
```

The `ensure_control_mode()` method automatically:
1. Reads the current mode from register 10
2. Writes the new mode if different
3. Verifies the write was successful

## Mode Compatibility

- **Commands must match mode**: Sending MIT commands while in VEL mode will not work correctly
- **CAN IDs differ**: Each mode uses a different arbitration ID
- **Register must match**: Register 10 must match the command format

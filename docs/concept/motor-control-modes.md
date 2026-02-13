---
tags:
  - concept
  - control-modes
  - reference
---

# Motor Control Modes

DaMiao motors support four different control modes, each optimized for different use cases.

## Overview

Control modes determine how the motor interprets command messages. The control mode is set via [register 10 (CTRL_MODE)](registers.md) and must match the command format being sent.

| Mode | Register Value | CAN ID Format | Use Case |
|------|---------------|---------------|----------|
| MIT | 1 | `motor_id` | Impedance control with stiffness/damping |
| POS_VEL | 2 | `0x100 + motor_id` | Trapezoidal motion profiles |
| VEL | 3 | `0x200 + motor_id` | Velocity control |
| FORCE_POS | 4 | `0x300 + motor_id` | Position control with limits |

## Mode Selection Guide

- **MIT**: Compliant/impedance control, force control, research applications
- **POS_VEL**: Smooth point-to-point motion, trapezoidal profiles, position accuracy
- **VEL**: Pure velocity control, constant-speed operation
- **FORCE_POS**: Safe positioning with force limits, human-robot interaction

## Switching Between Modes

The control mode must be set before sending commands.

API method: [`DaMiaoMotor.ensure_control_mode()`](../api/motor.md)

The `ensure_control_mode()` method automatically:
1. Reads the current mode from register 10
2. Writes the new mode if different
3. Verifies the write was successful

## Mode Compatibility

- **Commands must match mode**: Sending MIT commands while in VEL mode will not work correctly
- **CAN IDs differ**: Each mode uses a different arbitration ID
- **Register must match**: Register 10 must match the command format

## MIT Mode {#mit-mode}

**MIT mode** (named after MIT's Cheetah robot) provides impedance control with position, velocity, stiffness, damping, and feedforward torque.

API method: [`DaMiaoMotor.send_cmd_mit()`](../api/motor.md)

| Parameter | Range | Description |
|-----------|-------|-------------|
| `target_position` | Motor-specific | Desired position (radians) |
| `target_velocity` | Motor-specific | Desired velocity (rad/s) |
| `stiffness` (kp) | 0-500 | Position gain (stiffness) |
| `damping` (kd) | 0-5 | Velocity gain (damping) |
| `feedforward_torque` | Motor-specific | Feedforward torque (Nm) |

![MIT mode control law](control_law_mit.svg)

$$
T_{\text{ref}} = K_p \cdot (p_{\text{des}} - \theta_m) + K_d \cdot (v_{\text{des}} - \dot{\theta}_m) + \tau_{ff}
$$

$$
i_{q,\text{ref}} = \frac{T_{\text{ref}}}{K_T}, \quad i_{d,\text{ref}} = 0
$$

## POS_VEL Mode {#pos-vel-mode}

**POS_VEL mode** provides position-velocity control with trapezoidal motion profiles. The motor moves toward the target position, limiting velocity to the specified maximum, with automatic acceleration and deceleration.

API method: [`DaMiaoMotor.send_cmd_pos_vel()`](../api/motor.md)

| Parameter | Range | Description |
|-----------|-------|-------------|
| `target_position` | Motor-specific | Desired position (radians) |
| `velocity_limit` | Motor-specific | Maximum velocity during motion (rad/s) |

![POS_VEL mode control law](control_law_pos_vel.svg)

$$
v_{\text{des}} = \text{clip}\!\left(K_{p,\text{apr}} (p_{\text{des}} - \theta_m) + K_{i,\text{apr}} \int (p_{\text{des}} - \theta_m) \, dt,\; -v_{\text{target}},\; v_{\text{target}}\right)
$$

$$
i_{q,\text{ref}} = K_{p,\text{asr}} (v_{\text{des}} - \dot{\theta}_m) + K_{i,\text{asr}} \int (v_{\text{des}} - \dot{\theta}_m) \, dt, \quad i_{d,\text{ref}} = 0
$$

where \(v_{\text{target}}\) is the commanded `velocity_limit`, [KP_APR](registers.md) (reg 27), [KI_APR](registers.md) (reg 28) are position loop gains, and [KP_ASR](registers.md) (reg 25), [KI_ASR](registers.md) (reg 26) are speed loop gains.

## VEL Mode {#vel-mode}

**VEL mode** provides pure velocity control. The motor maintains the commanded velocity. Positive values rotate in one direction, negative values in the opposite direction.

API method: [`DaMiaoMotor.send_cmd_vel()`](../api/motor.md)

| Parameter | Range | Description |
|-----------|-------|-------------|
| `target_velocity` | Motor-specific | Desired velocity (rad/s) |

![VEL mode control law](control_law_vel.svg)

$$
i_{q,\text{ref}} = K_{p,\text{asr}} (v_{\text{des}} - \dot{\theta}_m) + K_{i,\text{asr}} \int (v_{\text{des}} - \dot{\theta}_m) \, dt, \quad i_{d,\text{ref}} = 0
$$

where [KP_ASR](registers.md) (reg 25) and [KI_ASR](registers.md) (reg 26) are speed loop gains.

## FORCE_POS Mode {#force-pos-mode}

**FORCE_POS mode** (Force-Position Hybrid) provides position control with velocity and current limits. The motor moves toward the target position while respecting the velocity and current limits, providing safe position control with force limiting.

API method: [`DaMiaoMotor.send_cmd_force_pos()`](../api/motor.md)

| Parameter | Range | Description |
|-----------|-------|-------------|
| `target_position` | Motor-specific | Desired position (radians) |
| `velocity_limit` | 0-100 rad/s | Maximum velocity during motion |
| `current_limit` | 0.0-1.0 | Torque current limit (normalized) |

![FORCE_POS mode control law](control_law_force_pos.svg)

$$
v_{\text{des}} = K_{p,\text{apr}} (p_{\text{des}} - \theta_m) + K_{i,\text{apr}} \int (p_{\text{des}} - \theta_m) \, dt
$$

$$
i_{q,\text{ref}} = \text{clip}\!\left(K_{p,\text{asr}} (v_{\text{des}} - \dot{\theta}_m) + K_{i,\text{asr}} \int (v_{\text{des}} - \dot{\theta}_m) \, dt,\; -\tau_{\text{lim}},\; \tau_{\text{lim}}\right), \quad i_{d,\text{ref}} = 0
$$

where [KP_APR](registers.md) (reg 27), [KI_APR](registers.md) (reg 28) are position loop gains, and [KP_ASR](registers.md) (reg 25), [KI_ASR](registers.md) (reg 26) are speed loop gains.

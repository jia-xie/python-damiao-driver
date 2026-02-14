---
tags:
  - concept
  - control-modes
  - reference
---

# Motor Control Modes

DaMiao motors support four different control modes, each optimized for different use cases.

Quick links:
<div class="mode-strip">
  <a class="mode-chip mode-chip-mit" href="#mit-mode">MIT</a>
  <a class="mode-chip mode-chip-posvel" href="#pos-vel-mode">POS_VEL</a>
  <a class="mode-chip mode-chip-vel" href="#vel-mode">VEL</a>
  <a class="mode-chip mode-chip-forcepos" href="#force-pos-mode">FORCE_POS</a>
</div>

!!! tip "Recommended learning path"
    To better understand the control modes in practice, use [`damiao gui`](../package-usage/web-gui.md) and switch between modes while observing live feedback and charts.

## Overview

Control modes determine how the motor interprets command messages. The control mode is set via [register 10 (CTRL_MODE)](registers.md) and must match the command format being sent.

API method: [`DaMiaoMotor.ensure_control_mode()`](../api/motor.md#damiao_motor.core.motor.DaMiaoMotor.ensure_control_mode)

Mode parameters marked as "Motor-specific" use the mapping limits for the selected motor type.
See [PMAX / VMAX / TMAX defaults](registers.md#pmax-vmax-tmax-defaults). These registers are writable, but changing them is generally not recommended.

The [`ensure_control_mode()`](../api/motor.md#damiao_motor.core.motor.DaMiaoMotor.ensure_control_mode) method automatically:

1. Reads the current mode from register 10

2. Writes the new mode if different

3. Verifies the write was successful


**FOC Inner Current Control (not directly exposed)**

At the motor communication level, users directly select and command these modes:
**MIT / POS_VEL / VEL / FORCE_POS**.
See [Communication Protocol - Message Types](communication-protocol.md#message-types) for the CAN command frames.

Inside the motor firmware, all four modes ultimately drive the same inner **FOC current loop**:

- The selected communication-level mode computes a current target.
- That current target is sent to a fast inner FOC controller.
- The inner controller continuously compares target current vs measured current and corrects PWM voltage to reduce the error.

- **$i_{q,\mathrm{ref}}$**: the target for the torque-producing current.
  Larger magnitude means stronger torque. Sign decides rotation direction.

- **$i_{d,\mathrm{ref}}$**: the target for the flux-axis current.
  In these modes it is set to `0`, meaning "do not add extra d-axis current."

!!! note "Note"
    The motor tracks the calculated $i_{q,\mathrm{ref}}$ to produce the desired torque, while keeping the d-axis current at $i_{d,\mathrm{ref}} = 0$.

| Mode | Easy interpretation of $i_{q,\mathrm{ref}}$ | $i_{d,\mathrm{ref}}$ |
|------|-------------------------------------|-------------|
| MIT | Calculated from position/velocity error + feedforward torque, then converted to current | `0` |
| POS_VEL | Position loop outputs a speed target, speed loop converts that speed error to current | `0` |
| VEL | Speed loop directly converts velocity error to current | `0` |
| FORCE_POS | Position loop and speed loop compute current, then it is clipped by current/force limit | `0` |

## <span class="mode-title mode-title-mit">MIT</span> Mode (Impedance Control) {#mit-mode}

**MIT mode** (named after MIT's Cheetah robot) provides impedance control with position, velocity, stiffness, damping, and feedforward torque.

API method: [`DaMiaoMotor.send_cmd_mit()`](../api/motor.md#damiao_motor.core.motor.DaMiaoMotor.send_cmd_mit)

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

Notation mapping: \(p_{\text{des}}\) = `target_position`, \(v_{\text{des}}\) = `target_velocity`, and \(\tau_{ff}\) = `feedforward_torque`.

where \(K_T\) comes from [KT_Value (register 1)](registers.md#reg-1-kt-value).

## <span class="mode-title mode-title-posvel">POS_VEL</span> Mode (Position + Velocity-Limit) {#pos-vel-mode}

**POS_VEL mode** provides position-velocity control with trapezoidal motion profiles. The motor moves toward the target position, limiting velocity to the specified maximum, with automatic acceleration and deceleration.

API method: [`DaMiaoMotor.send_cmd_pos_vel()`](../api/motor.md#damiao_motor.core.motor.DaMiaoMotor.send_cmd_pos_vel)

| Parameter | Range | Description |
|-----------|-------|-------------|
| `target_position` | Motor-specific | Desired position (radians) |
| `velocity_limit` | Motor-specific | Maximum velocity during motion (rad/s) |

![POS_VEL mode control law](control_law_pos_vel.svg)

$$
v_{\text{des}} = \text{clip}\!\left(K_{p,\text{apr}} (p_{\text{des}} - \theta_m) + K_{i,\text{apr}} \int (p_{\text{des}} - \theta_m) \, dt,\; -v_{\text{limit}},\; v_{\text{limit}}\right)
$$

Notation mapping: \(p_{\text{des}}\) = `target_position`, \(v_{\text{limit}}\) = `velocity_limit`; \(v_{\text{des}}\) is an internal speed target generated by the position loop.

In the control-law diagram, `velocity_limit` directly sets the clip bounds \(\pm v_{\text{limit}}\).

$$
i_{q,\text{ref}} = K_{p,\text{asr}} (v_{\text{des}} - \dot{\theta}_m) + K_{i,\text{asr}} \int (v_{\text{des}} - \dot{\theta}_m) \, dt, \quad i_{d,\text{ref}} = 0
$$

where \(v_{\text{limit}}\) is the commanded `velocity_limit`, [KP_APR](registers.md#reg-27-kp-apr) (reg 27), [KI_APR](registers.md#reg-28-ki-apr) (reg 28) are position loop gains, and [KP_ASR](registers.md#reg-25-kp-asr) (reg 25), [KI_ASR](registers.md#reg-26-ki-asr) (reg 26) are speed loop gains.

## <span class="mode-title mode-title-vel">VEL</span> Mode (Velocity) {#vel-mode}

**VEL mode** provides pure velocity control. The motor maintains the commanded velocity. Positive values rotate in one direction, negative values in the opposite direction.

API method: [`DaMiaoMotor.send_cmd_vel()`](../api/motor.md#damiao_motor.core.motor.DaMiaoMotor.send_cmd_vel)

| Parameter | Range | Description |
|-----------|-------|-------------|
| `target_velocity` | Motor-specific | Desired velocity (rad/s) |

![VEL mode control law](control_law_vel.svg)

$$
i_{q,\text{ref}} = K_{p,\text{asr}} (v_{\text{des}} - \dot{\theta}_m) + K_{i,\text{asr}} \int (v_{\text{des}} - \dot{\theta}_m) \, dt, \quad i_{d,\text{ref}} = 0
$$

Notation mapping: \(v_{\text{des}}\) = `target_velocity`.

where [KP_ASR](registers.md#reg-25-kp-asr) (reg 25) and [KI_ASR](registers.md#reg-26-ki-asr) (reg 26) are speed loop gains.

## <span class="mode-title mode-title-forcepos">FORCE_POS</span> Mode (Force-Limited Position) {#force-pos-mode}

**FORCE_POS mode** (Force-Position Hybrid) provides position control with velocity and torque-limit-ratio constraints. The motor moves toward the target position while respecting these limits, providing safe position control with force limiting.

API method: [`DaMiaoMotor.send_cmd_force_pos()`](../api/motor.md#damiao_motor.core.motor.DaMiaoMotor.send_cmd_force_pos)

| Parameter | Range | Description |
|-----------|-------|-------------|
| `target_position` | Motor-specific | Desired position (radians) |
| `velocity_limit` | 0-100 rad/s | Maximum velocity during motion |
| `torque_limit_ratio` | 0.0-1.0 | Normalized torque-limit coefficient |

![FORCE_POS mode control law](control_law_force_pos.svg)

$$
v_{\text{des}} = \text{clip}\!\left(K_{p,\text{apr}} (p_{\text{des}} - \theta_m) + K_{i,\text{apr}} \int (p_{\text{des}} - \theta_m) \, dt,\; -v_{\text{limit}},\; v_{\text{limit}}\right)
$$

$$
i_{q,\text{ref}} = \text{clip}\!\left(K_{p,\text{asr}} (v_{\text{des}} - \dot{\theta}_m) + K_{i,\text{asr}} \int (v_{\text{des}} - \dot{\theta}_m) \, dt,\; -\tau_{\text{lim}},\; \tau_{\text{lim}}\right), \quad i_{d,\text{ref}} = 0
$$

Notation mapping: \(p_{\text{des}}\) = `target_position`, \(v_{\text{limit}}\) = `velocity_limit`; \(v_{\text{des}}\) is an internal speed target generated by the position loop.

In FORCE_POS mode:

$$
\tau_{\text{lim}} = \text{torque_limit_ratio} \cdot T_{\max}
$$

Here \(T_{\max}\) is the max torque for the selected motor type (for example, for `4340`, \(T_{\max}=28\) Nm, so `torque_limit_ratio=0.5` gives \(\tau_{\text{lim}}=14\) Nm).

Also, \(v_{\text{limit}}\) is the commanded `velocity_limit`, [KP_APR](registers.md#reg-27-kp-apr) (reg 27), [KI_APR](registers.md#reg-28-ki-apr) (reg 28) are position loop gains, and [KP_ASR](registers.md#reg-25-kp-asr) (reg 25), [KI_ASR](registers.md#reg-26-ki-asr) (reg 26) are speed loop gains.

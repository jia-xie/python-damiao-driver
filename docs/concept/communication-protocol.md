---
tags:
  - concept
  - protocol
  - advanced
---

# Communication Protocol

This document describes the CAN bus communication protocol used by DaMiao motors.

## Overview

DaMiao motors communicate over CAN bus using a custom protocol. The protocol supports:

- **Command messages**: Send control commands to motors
- **Feedback messages**: Receive motor state information
- **Register operations**: Read/write motor configuration registers

## Message Types

**1. Control Commands**

Control commands send motion commands to motors. All frames are standard CAN (`STD`) with 8-byte data payload (`D[0]..D[7]`).

**MIT command frame** ([MIT mode](motor-control-modes.md#mit-mode))

<div class="protocol-frame" markdown="1">

| Arbitration ID | Attribute | D[0] | D[1] | D[2] | D[3] | D[4] | D[5] | D[6] | D[7] |
|---|---|---|---|---|---|---|---|---|---|
| `motor_id` | `STD` | <span class="bm bm-pos">`pos_u[15:8]`</span> | <span class="bm bm-pos">`pos_u[7:0]`</span> | <span class="bm bm-vel">`vel_u[11:4]`</span> | <span class="bm bm-vel">`vel_u[3:0]`</span> / <span class="bm bm-kp">`kp_u[11:8]`</span> | <span class="bm bm-kp">`kp_u[7:0]`</span> | <span class="bm bm-kd">`kd_u[11:4]`</span> | <span class="bm bm-kd">`kd_u[3:0]`</span> / <span class="bm bm-torque">`torq_u[11:8]`</span> | <span class="bm bm-torque">`torq_u[7:0]`</span> |

</div>

**POS_VEL command frame** ([POS_VEL mode](motor-control-modes.md#pos-vel-mode), little-endian)

<div class="protocol-frame" markdown="1">

| Arbitration ID | Attribute | D[0] | D[1] | D[2] | D[3] | D[4] | D[5] | D[6] | D[7] |
|---|---|---|---|---|---|---|---|---|---|
| `0x100 + motor_id` | `STD` | <span class="bm bm-pos">`position_b0`</span> | <span class="bm bm-pos">`position_b1`</span> | <span class="bm bm-pos">`position_b2`</span> | <span class="bm bm-pos">`position_b3`</span> | <span class="bm bm-vel">`vel_limit_b0`</span> | <span class="bm bm-vel">`vel_limit_b1`</span> | <span class="bm bm-vel">`vel_limit_b2`</span> | <span class="bm bm-vel">`vel_limit_b3`</span> |

</div>

**VEL command frame** ([VEL mode](motor-control-modes.md#vel-mode), little-endian)

<div class="protocol-frame" markdown="1">

| Arbitration ID | Attribute | D[0] | D[1] | D[2] | D[3] | D[4] | D[5] | D[6] | D[7] |
|---|---|---|---|---|---|---|---|---|---|
| `0x200 + motor_id` | `STD` | <span class="bm bm-vel">`velocity_b0`</span> | <span class="bm bm-vel">`velocity_b1`</span> | <span class="bm bm-vel">`velocity_b2`</span> | <span class="bm bm-vel">`velocity_b3`</span> | <span class="bm bm-pad">`0x00`</span> | <span class="bm bm-pad">`0x00`</span> | <span class="bm bm-pad">`0x00`</span> | <span class="bm bm-pad">`0x00`</span> |

</div>

**FORCE_POS command frame** ([FORCE_POS mode](motor-control-modes.md#force-pos-mode), little-endian)

<div class="protocol-frame" markdown="1">

| Arbitration ID | Attribute | D[0] | D[1] | D[2] | D[3] | D[4] | D[5] | D[6] | D[7] |
|---|---|---|---|---|---|---|---|---|---|
| `0x300 + motor_id` | `STD` | <span class="bm bm-pos">`position_b0`</span> | <span class="bm bm-pos">`position_b1`</span> | <span class="bm bm-pos">`position_b2`</span> | <span class="bm bm-pos">`position_b3`</span> | <span class="bm bm-vel">`vel_limit_b0`</span> | <span class="bm bm-vel">`vel_limit_b1`</span> | <span class="bm bm-torque">`torque_ratio_b0`</span> | <span class="bm bm-torque">`torque_ratio_b1`</span> |

</div>

`b0` is the least significant byte (LSB), `b3` is the most significant byte (MSB).

**2. System Commands**

System commands also use `arbitration_id = motor_id` and `STD` frames:

<div class="protocol-frame" markdown="1">

| Command | Arbitration ID | Attribute | D[0] | D[1] | D[2] | D[3] | D[4] | D[5] | D[6] | D[7] |
|---|---|---|---|---|---|---|---|---|---|---|
| Enable motor | `motor_id` | `STD` | `0xFF` | `0xFF` | `0xFF` | `0xFF` | `0xFF` | `0xFF` | `0xFF` | `0xFC` |
| Disable motor | `motor_id` | `STD` | `0xFF` | `0xFF` | `0xFF` | `0xFF` | `0xFF` | `0xFF` | `0xFF` | `0xFD` |
| Set zero position | `motor_id` | `STD` | `0xFF` | `0xFF` | `0xFF` | `0xFF` | `0xFF` | `0xFF` | `0xFF` | `0xFE` |
| Clear error | `motor_id` | `STD` | `0xFF` | `0xFF` | `0xFF` | `0xFF` | `0xFF` | `0xFF` | `0xFF` | `0xFB` |

</div>

**3. Register Operations**

Register command requests use arbitration ID `0x7FF` and `STD` frames:

For register semantics and persistence behavior:

- See [Registers: How it works?](registers.md#how-it-works) for write (RAM/runtime) vs store (flash persistence) behavior ([`write_register(...)`](../api/motor.md#damiao_motor.core.motor.DaMiaoMotor.write_register) vs [`store_parameters()`](../api/motor.md#damiao_motor.core.motor.DaMiaoMotor.store_parameters)).
- See [Register Table](registers.md#register-table) for valid `RID`, access type (`RW`/`RO`), value range, and data type.
- Terminology used in this documentation: **write** = runtime RAM update, **store** = persist to flash.

**Read register request (`D[2] = 0x33`)**

<div class="protocol-frame" markdown="1">

| Arbitration ID | Attribute | D[0] | D[1] | D[2] | D[3] | D[4] | D[5] | D[6] | D[7] |
|---|---|---|---|---|---|---|---|---|---|
| `0x7FF` | `STD` | <span class="bm bm-canid">`CANID_L`</span> | <span class="bm bm-canid">`CANID_H`</span> | <span class="bm bm-read">`0x33`</span> | <span class="bm bm-rid">`RID`</span> | <span class="bm bm-pad">`0x00`</span> | <span class="bm bm-pad">`0x00`</span> | <span class="bm bm-pad">`0x00`</span> | <span class="bm bm-pad">`0x00`</span> |

</div>

**Write register request (`D[2] = 0x55`)**

<div class="protocol-frame" markdown="1">

| Arbitration ID | Attribute | D[0] | D[1] | D[2] | D[3] | D[4] | D[5] | D[6] | D[7] |
|---|---|---|---|---|---|---|---|---|---|
| `0x7FF` | `STD` | <span class="bm bm-canid">`CANID_L`</span> | <span class="bm bm-canid">`CANID_H`</span> | <span class="bm bm-write">`0x55`</span> | <span class="bm bm-rid">`RID`</span> | <span class="bm bm-value">`data_b0`</span> | <span class="bm bm-value">`data_b1`</span> | <span class="bm bm-value">`data_b2`</span> | <span class="bm bm-value">`data_b3`</span> |

</div>

**Store parameters request (`D[2] = 0xAA`)**

<div class="protocol-frame" markdown="1">

| Arbitration ID | Attribute | D[0] | D[1] | D[2] | D[3] | D[4] | D[5] | D[6] | D[7] |
|---|---|---|---|---|---|---|---|---|---|
| `0x7FF` | `STD` | <span class="bm bm-canid">`CANID_L`</span> | <span class="bm bm-canid">`CANID_H`</span> | <span class="bm bm-store">`0xAA`</span> | <span class="bm bm-rid">`RID` (driver uses `0x01`)</span> | <span class="bm bm-pad">`0x00`</span> | <span class="bm bm-pad">`0x00`</span> | <span class="bm bm-pad">`0x00`</span> | <span class="bm bm-pad">`0x00`</span> |

</div>

**4. Feedback Messages**

Motors continuously send feedback as `STD` frames:

<div class="protocol-frame" markdown="1">

| Arbitration ID | Attribute | D[0] | D[1] | D[2] | D[3] | D[4] | D[5] | D[6] | D[7] |
|---|---|---|---|---|---|---|---|---|---|
| `feedback_id` (MST_ID, reg 7) | `STD` | <span class="bm bm-status">`status[7:4]`</span> / <span class="bm bm-mid">`motor_id[3:0]`</span> | <span class="bm bm-pos">`pos_u[15:8]`</span> | <span class="bm bm-pos">`pos_u[7:0]`</span> | <span class="bm bm-vel">`vel_u[11:4]`</span> | <span class="bm bm-vel">`vel_u[3:0]`</span> / <span class="bm bm-torque">`torq_u[11:8]`</span> | <span class="bm bm-torque">`torq_u[7:0]`</span> | <span class="bm bm-temp">`T_mos`</span> | <span class="bm bm-temp">`T_rotor`</span> |

</div>

#### Status Codes

| Group | Code | Name | Description |
|------|------|------|-------------|
| Normal | `0x0` | DISABLED | Motor is disabled |
| Normal | `0x1` | ENABLED | Motor is enabled and ready |
| Fault | `0x8` | <span id="status-over-voltage"></span>OVER_VOLTAGE | Over-voltage protection triggered (threshold: [OV_Value reg 29](registers.md#reg-29-ov-value)) |
| Fault | `0x9` | <span id="status-under-voltage"></span>UNDER_VOLTAGE | Under-voltage protection triggered (threshold: [UV_Value reg 0](registers.md#reg-0-uv-value)) |
| Fault | `0xA` | <span id="status-over-current"></span>OVER_CURRENT | Over-current protection triggered (threshold: [OC_Value reg 3](registers.md#reg-3-oc-value)) |
| Fault | `0xB` | <span id="status-over-temp"></span>MOS_OVER_TEMP | MOSFET over-temperature protection triggered (threshold: [OT_Value reg 2](registers.md#reg-2-ot-value)) |
| Fault | `0xC` | ROTOR_OVER_TEMP | Rotor over-temperature protection triggered (threshold: [OT_Value reg 2](registers.md#reg-2-ot-value)) |
| Fault | `0xD` | <span id="status-lost-comm"></span>LOST_COMM | Communication timeout/loss detected (related: [TIMEOUT reg 9](registers.md#reg-9-timeout), where 1 register unit = 50 microseconds) |
| Fault | `0xE` | OVERLOAD | Motor overload detected |

**5. Register Reply Messages**

Register read replies are `STD` frames:

<div class="protocol-frame" markdown="1">

| Arbitration ID | Attribute | D[0] | D[1] | D[2] | D[3] | D[4] | D[5] | D[6] | D[7] |
|---|---|---|---|---|---|---|---|---|---|
| `feedback_id` (MST_ID, reg 7) | `STD` | <span class="bm bm-canid">`CANID_L`</span> | <span class="bm bm-canid">`CANID_H`</span> | <span class="bm bm-read">`0x33`</span> | <span class="bm bm-rid">`RID`</span> | <span class="bm bm-value">`data_b0`</span> | <span class="bm bm-value">`data_b1`</span> | <span class="bm bm-value">`data_b2`</span> | <span class="bm bm-value">`data_b3`</span> |

</div>

## Data Encoding

**Position/Velocity/Torque Encoding**

Position, velocity, and torque values are encoded using a mapping function:

$$
u=\frac{x-x_{\min}}{x_{\max}-x_{\min}}\left(2^{N}-1\right)
$$

Where:
- `x_{\min}` and `x_{\max}` are motor-specific limits (from motor type presets; see [PMAX / VMAX / TMAX defaults](registers.md#pmax-vmax-tmax-defaults))
- `N` is the bit width (16 for position, 12 for velocity/torque)
- `u` is the encoded unsigned integer value

Decoding reverses this process:

$$
x=x_{\min}+\frac{u}{2^{N}-1}\left(x_{\max}-x_{\min}\right)
$$

**Stiffness/Damping Encoding**

Stiffness (kp) and damping (kd) use fixed ranges:

- **Stiffness**: 0-500 (12-bit encoding)
- **Damping**: 0-5 (12-bit encoding)

## Multi-Motor Communication

Multiple motors can share the same CAN bus:

1. Each motor has a unique `motor_id` (ESC_ID, register 8)
2. Each motor has a `feedback_id` (MST_ID, register 7); unique assignment is recommended
3. Commands are addressed to specific `motor_id`
4. Feedback is identified by `feedback_id`

**@remarks**

Each motor has a unique `feedback_id` (MST_ID, register 7) that identifies the motor in feedback messages.
While the `feedback_id` does not strictly need to be unique for each motor (since the motor ID is included in the data frame),
it is recommended to assign unique `feedback_id`s to avoid confusion and simplify message routing.

**@see** [Message frame structure](#message-types) for details on motor ID encoding in feedback messages.

**Example: Three Motors**

Motor ID assignment:

| Motor | `motor_id` (ESC_ID, reg 8) | `feedback_id` (MST_ID, reg 7) |
|-------|-----------------------------|--------------------------------|
| Motor 1 | `0x01` | `0x11` |
| Motor 2 | `0x02` | `0x12` |
| Motor 3 | `0x03` | `0x13` |

[MIT mode](motor-control-modes.md#mit-mode) command arbitration IDs (`arbitration_id = motor_id`):

| Motor | Arbitration ID |
|-------|----------------|
| Motor 1 | `0x001` |
| Motor 2 | `0x002` |
| Motor 3 | `0x003` |

Feedback arbitration IDs (`arbitration_id = feedback_id`):

| Motor | Arbitration ID |
|-------|----------------|
| Motor 1 | `0x011` |
| Motor 2 | `0x012` |
| Motor 3 | `0x013` |

## Error Handling

**Timeout Protection**

- Register operations have timeout protection
- If no reply received within timeout, operation fails
- Motor has CAN timeout alarm ([TIMEOUT register 9](registers.md#reg-9-timeout)); Register 9 stores timeout in units of 50 microseconds (1 register unit = 50 microseconds), and motor disables if no commands are received
- Timeout-related status is reported as [LOST_COMM (`0xD`)](#status-lost-comm)

**Error States**

- Motor enters error state on various conditions (overcurrent, overtemperature, etc.)
- Error state is reported in feedback status byte
- Use clear error command to reset error state

## Protocol Limitations

1. **Message size**: Fixed 8 bytes (CAN limitation)
2. **Arbitration ID range**: 0x000-0x7FF (11-bit standard CAN)
3. **Bitrate**: Must match across all devices
4. **Real-time**: No guaranteed delivery time (best-effort)

## Further Reading

- See [Motor Control Modes](motor-control-modes.md) for control mode details
- See [CAN Bus Fundamentals](can.md) for CAN bus basics
- For interactive understanding of control modes, use [`damiao gui`](../package-usage/web-gui.md)
- See [API Reference](../api/motor.md) for implementation details

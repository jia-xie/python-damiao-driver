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

Control commands send motion commands to motors. Each [control mode](motor-control-modes.md) uses a different arbitration ID and fixed 8-byte payload.

| Mode | Arbitration ID | Payload |
|------|----------------|---------|
| [MIT](motor-control-modes.md#mit-mode) | `motor_id` | 8-byte packed P/V/Kp/Kd/T command |
| [POS_VEL](motor-control-modes.md#pos-vel-mode) | `0x100 + motor_id` | 8-byte payload (`float32` position + `float32` velocity limit) |
| [VEL](motor-control-modes.md#vel-mode) | `0x200 + motor_id` | 8-byte payload (`float32` velocity + 4-byte zero padding) |
| [FORCE_POS](motor-control-modes.md#force-pos-mode) | `0x300 + motor_id` | 8-byte payload (`float32` position + `uint16` velocity limit + `uint16` torque limit ratio) |

Control payload byte maps:

**MIT payload (8 bytes, packed)**

| Byte | Bits | Field |
|------|------|-------|
| `0` | `7:0` | <span class="bm bm-pos">`pos_u[15:8]`</span> |
| `1` | `7:0` | <span class="bm bm-pos">`pos_u[7:0]`</span> |
| `2` | `7:0` | <span class="bm bm-vel">`vel_u[11:4]`</span> |
| `3` | `7:4` / `3:0` | <span class="bm bm-vel">`vel_u[3:0]`</span> / <span class="bm bm-kp">`kp_u[11:8]`</span> |
| `4` | `7:0` | <span class="bm bm-kp">`kp_u[7:0]`</span> |
| `5` | `7:0` | <span class="bm bm-kd">`kd_u[11:4]`</span> |
| `6` | `7:4` / `3:0` | <span class="bm bm-kd">`kd_u[3:0]`</span> / <span class="bm bm-torque">`torq_u[11:8]`</span> |
| `7` | `7:0` | <span class="bm bm-torque">`torq_u[7:0]`</span> |

**POS_VEL payload (8 bytes, little-endian)**

| Byte | Field |
|------|-------|
| `0-3` | <span class="bm bm-pos">`target_position` (`float32`)</span> |
| `4-7` | <span class="bm bm-vel">`velocity_limit` (`float32`)</span> |

**VEL payload (8 bytes, little-endian)**

| Byte | Field |
|------|-------|
| `0-3` | <span class="bm bm-vel">`target_velocity` (`float32`)</span> |
| `4-7` | <span class="bm bm-pad">padding (`0x00 0x00 0x00 0x00`)</span> |

**FORCE_POS payload (8 bytes, little-endian)**

| Byte | Field |
|------|-------|
| `0-3` | <span class="bm bm-pos">`target_position` (`float32`)</span> |
| `4-5` | <span class="bm bm-vel">`velocity_limit` (`uint16`, scaled)</span> |
| `6-7` | <span class="bm bm-torque">`torque_limit_ratio` (`uint16`, scaled)</span> |

**2. System Commands**

System commands use `arbitration_id = motor_id` and fixed 8-byte payloads:

| Command | Data |
|---------|------|
| Enable motor | `[FF, FF, FF, FF, FF, FF, FF, FC]` |
| Disable motor | `[FF, FF, FF, FF, FF, FF, FF, FD]` |
| Set zero position | `[FF, FF, FF, FF, FF, FF, FF, FE]` |
| Clear error | `[FF, FF, FF, FF, FF, FF, FF, FB]` |

**3. Register Operations**

Register operations use arbitration ID `0x7FF` and 8-byte payloads.

Read request byte map (`Byte 2 = 0x33`):

| Byte | Field |
|------|-------|
| `0` | <span class="bm bm-canid">`CANID_L`</span> |
| `1` | <span class="bm bm-canid">`CANID_H`</span> |
| `2` | <span class="bm bm-read">`0x33` (read command)</span> |
| `3` | <span class="bm bm-rid">Register ID (`RID`)</span> |
| `4-7` | <span class="bm bm-pad">`0x00 0x00 0x00 0x00` (don't care)</span> |

Write request byte map (`Byte 2 = 0x55`):

| Byte | Field |
|------|-------|
| `0` | <span class="bm bm-canid">`CANID_L`</span> |
| `1` | <span class="bm bm-canid">`CANID_H`</span> |
| `2` | <span class="bm bm-write">`0x55` (write command)</span> |
| `3` | <span class="bm bm-rid">Register ID (`RID`)</span> |
| `4-7` | <span class="bm bm-value">Register value (4 bytes)</span> |

Store request byte map (`Byte 2 = 0xAA`):

| Byte | Field |
|------|-------|
| `0` | <span class="bm bm-canid">`CANID_L`</span> |
| `1` | <span class="bm bm-canid">`CANID_H`</span> |
| `2` | <span class="bm bm-store">`0xAA` (store command)</span> |
| `3` | <span class="bm bm-rid">Store selector (`RID`, driver uses `0x01`)</span> |
| `4-7` | <span class="bm bm-pad">`0x00 0x00 0x00 0x00` (don't care)</span> |

**4. Feedback Messages**

Motors continuously send 8-byte state frames with `arbitration_id = feedback_id` (MST_ID, register 7):

| Byte | Bits | Meaning |
|------|------|---------|
| `0` | `7:4` / `3:0` | <span class="bm bm-status">Status code</span> / <span class="bm bm-mid">Motor ID</span> |
| `1` | `7:0` | <span class="bm bm-pos">Position `pos_u[15:8]`</span> |
| `2` | `7:0` | <span class="bm bm-pos">Position `pos_u[7:0]`</span> |
| `3` | `7:0` | <span class="bm bm-vel">Velocity `vel_u[11:4]`</span> |
| `4` | `7:4` / `3:0` | <span class="bm bm-vel">Velocity `vel_u[3:0]`</span> / <span class="bm bm-torque">Torque `torq_u[11:8]`</span> |
| `5` | `7:0` | <span class="bm bm-torque">Torque `torq_u[7:0]`</span> |
| `6` | `7:0` | <span class="bm bm-temp">MOSFET temperature (degC)</span> |
| `7` | `7:0` | <span class="bm bm-temp">Rotor temperature (degC)</span> |

#### Status Codes

| Code | Name | Description |
|------|------|-------------|
| `0x0` | DISABLED | Motor is disabled |
| `0x1` | ENABLED | Motor is enabled and ready |
| `0x8` | <span id="status-over-voltage"></span>OVER_VOLTAGE | Over-voltage protection triggered (threshold: [OV_Value reg 29](registers.md#reg-29-ov-value)) |
| `0x9` | <span id="status-under-voltage"></span>UNDER_VOLTAGE | Under-voltage protection triggered (threshold: [UV_Value reg 0](registers.md#reg-0-uv-value)) |
| `0xA` | <span id="status-over-current"></span>OVER_CURRENT | Over-current protection triggered (threshold: [OC_Value reg 3](registers.md#reg-3-oc-value)) |
| `0xB` | <span id="status-over-temp"></span>MOS_OVER_TEMP | MOSFET over-temperature protection triggered (threshold: [OT_Value reg 2](registers.md#reg-2-ot-value)) |
| `0xC` | ROTOR_OVER_TEMP | Rotor over-temperature protection triggered (threshold: [OT_Value reg 2](registers.md#reg-2-ot-value)) |
| `0xD` | <span id="status-lost-comm"></span>LOST_COMM | Communication timeout/loss detected (related: [TIMEOUT reg 9](registers.md#reg-9-timeout)) |
| `0xE` | OVERLOAD | Motor overload detected |

**5. Register Reply Messages**

Register read replies use `arbitration_id = feedback_id` (MST_ID), 8-byte payload:

| Byte | Meaning |
|------|---------|
| `0` | <span class="bm bm-canid">`CANID_L`</span> |
| `1` | <span class="bm bm-canid">`CANID_H`</span> |
| `2` | <span class="bm bm-read">Reply marker (`0x33`)</span> |
| `3` | <span class="bm bm-rid">Register ID (`RID`)</span> |
| `4-7` | <span class="bm bm-value">Register value (4 bytes)</span> |

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
- Motor has CAN timeout alarm ([TIMEOUT register 9](registers.md#reg-9-timeout)); motor disables if no commands are received
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

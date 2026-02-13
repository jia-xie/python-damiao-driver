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
| [MIT](motor-control-modes.md#mit-mode) | `motor_id` | Packed position/velocity/stiffness/damping/feedforward torque |
| [POS_VEL](motor-control-modes.md#pos-vel-mode) | `0x100 + motor_id` | `Byte 0-3`: position (`float`), `Byte 4-7`: velocity limit (`float`) |
| [VEL](motor-control-modes.md#vel-mode) | `0x200 + motor_id` | `Byte 0-3`: target velocity (`float`), `Byte 4-7`: padding (`0x00`) |
| [FORCE_POS](motor-control-modes.md#force-pos-mode) | `0x300 + motor_id` | `Byte 0-3`: position (`float`), `Byte 4-5`: velocity limit (`uint16`), `Byte 6-7`: torque limit ratio (`uint16`) |

**2. System Commands**

System commands use `arbitration_id = motor_id` and fixed 8-byte payloads:

| Command | Data |
|---------|------|
| Enable motor | `[FF, FF, FF, FF, FF, FF, FF, FC]` |
| Disable motor | `[FF, FF, FF, FF, FF, FF, FF, FD]` |
| Set zero position | `[FF, FF, FF, FF, FF, FF, FF, FE]` |
| Clear error | `[FF, FF, FF, FF, FF, FF, FF, FB]` |

**3. Register Operations**

Register operations use a unified format with arbitration ID `0x7FF`:

| Operation | Byte 2 | Byte 3 | Byte 4-7 |
|-----------|--------|--------|----------|
| Read | `0x33` | Register ID (`RID`) | Don't care (`0x00`) |
| Write | `0x55` | Register ID (`RID`) | Register value (4 bytes) |
| Store | `0xAA` | Register ID (`RID`, usually `0x00`) | Don't care (`0x00`) |

Common prefix: `Byte 0-1 = CAN ID` (low byte, high byte).

**4. Feedback Messages**

Motors continuously send 8-byte state frames with `arbitration_id = feedback_id` (MST_ID, register 7):

| Bytes | Meaning |
|-------|---------|
| `0` | Status (high 4 bits) + Motor ID (low 4 bits) |
| `1-2` | Position (16-bit mapped) |
| `3-4` | Velocity (12-bit mapped) |
| `5` | Torque (12-bit mapped, split across bytes 4/5) |
| `6` | MOSFET temperature (°C) |
| `7` | Rotor temperature (°C) |

#### Status Codes

| Code | Name | Description |
|------|------|-------------|
| `0x0` | DISABLED | Motor is disabled |
| `0x1` | ENABLED | Motor is enabled and ready |
| `0x8` | OVER_VOLTAGE | Over-voltage protection triggered |
| `0x9` | UNDER_VOLTAGE | Under-voltage protection triggered |
| `0xA` | OVER_CURRENT | Over-current protection triggered |
| `0xB` | MOS_OVER_TEMP | MOSFET over-temperature protection triggered |
| `0xC` | ROTOR_OVER_TEMP | Rotor over-temperature protection triggered |
| `0xD` | LOST_COMM | Communication timeout/loss detected |
| `0xE` | OVERLOAD | Motor overload detected |

**5. Register Reply Messages**

Register read replies use `arbitration_id = feedback_id` (MST_ID), 8-byte payload:

| Bytes | Meaning |
|-------|---------|
| `0-2` | CAN ID encoding |
| `3` | Register ID (`RID`) |
| `4-7` | Register value (4 bytes) |

## Data Encoding

**Position/Velocity/Torque Encoding**

Position, velocity, and torque values are encoded using a mapping function:

```
uint_value = (float_value - min) / (max - min) * (2^bits - 1)
```

Where:
- `min` and `max` are motor-specific limits (from motor type presets)
- `bits` is the bit width (16 for position, 12 for velocity/torque)

Decoding reverses this process:

```
float_value = min + (uint_value / (2^bits - 1)) * (max - min)
```

**Stiffness/Damping Encoding**

Stiffness (kp) and damping (kd) use fixed ranges:

- **Stiffness**: 0-500 (12-bit encoding)
- **Damping**: 0-5 (12-bit encoding)

## Message Timing

**Command Frequency**

- **Recommended**: 100-1000 Hz
- **Minimum**: ~10 Hz (for basic control)
- **Maximum**: Limited by CAN bus bandwidth

**Feedback Frequency**

- Motors send feedback automatically
- Typical frequency: 100-1000 Hz (depends on motor firmware)
- Feedback is asynchronous (not tied to command timing)

**Register Operations**

- Register reads/writes are request-reply operations
- Typical timeout: 100-500 ms
- Store operations may take longer (flash write)

## Multi-Motor Communication

Multiple motors can share the same CAN bus:

1. Each motor has a unique `motor_id` (ESC_ID, register 8)
2. Each motor has a unique `feedback_id` (MST_ID, register 7)
3. Commands are addressed to specific `motor_id`
4. Feedback is identified by `feedback_id`

**Example: Three Motors**

```
Motor 1: motor_id=0x01, feedback_id=0x11
Motor 2: motor_id=0x02, feedback_id=0x12
Motor 3: motor_id=0x03, feedback_id=0x13

[MIT mode](motor-control-modes.md#mit-mode) commands:
  Motor 1: arbitration_id = 0x001
  Motor 2: arbitration_id = 0x002
  Motor 3: arbitration_id = 0x003

Feedback:
  Motor 1: arbitration_id = 0x011
  Motor 2: arbitration_id = 0x012
  Motor 3: arbitration_id = 0x013
```

## Error Handling

**Timeout Protection**

- Register operations have timeout protection
- If no reply received within timeout, operation fails
- Motor has CAN timeout alarm (register 9) - motor disables if no commands received

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

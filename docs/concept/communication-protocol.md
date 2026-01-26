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

### 1. Control Commands

Control commands send motion commands to motors. Each control mode uses a different arbitration ID.

#### MIT Mode Command

- **Arbitration ID**: `motor_id` (e.g., 0x001 for motor ID 1)
- **Data Format**: 8 bytes encoding position, velocity, stiffness, damping, and feedforward torque

```
Byte 0-1: Position (16-bit, mapped to motor's position range)
Byte 2-3: Velocity (12-bit, mapped to motor's velocity range)
Byte 4-5: Stiffness (kp) (12-bit, 0-500)
Byte 6-7: Damping (kd) (12-bit, 0-5)
Byte 7:   Feedforward torque (12-bit, mapped to motor's torque range)
```

#### POS_VEL Mode Command

- **Arbitration ID**: `0x100 + motor_id`
- **Data Format**: 8 bytes (two 32-bit floats)

```
Byte 0-3: Target position (float, radians)
Byte 4-7: Target velocity (float, rad/s)
```

#### VEL Mode Command

- **Arbitration ID**: `0x200 + motor_id`
- **Data Format**: 8 bytes (one 32-bit float + padding)

```
Byte 0-3: Target velocity (float, rad/s)
Byte 4-7: Padding (0x00)
```

#### FORCE_POS Mode Command

- **Arbitration ID**: `0x300 + motor_id`
- **Data Format**: 8 bytes (float + two uint16)

```
Byte 0-3: Target position (float, radians)
Byte 4-5: Velocity limit (uint16, 0-10000, represents 0-100 rad/s)
Byte 6-7: Current limit (uint16, 0-10000, represents 0.0-1.0 normalized)
```

### 2. System Commands

System commands use special message formats:

#### Enable Motor

- **Arbitration ID**: `motor_id`
- **Data**: `[0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFC]`

#### Disable Motor

- **Arbitration ID**: `motor_id`
- **Data**: `[0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFD]`

#### Set Zero Position

- **Arbitration ID**: `motor_id`
- **Data**: `[0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFE]`

#### Clear Error

- **Arbitration ID**: `motor_id`
- **Data**: `[0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFB]`

### 3. Register Operations

Register operations use a unified format with arbitration ID `0x7FF`:

#### Register Read Request

```
Byte 0-1: CAN ID (low byte, high byte)
Byte 2:   0x33 (read command)
Byte 3:   Register ID (RID)
Byte 4-7: Don't care (0x00)
```

#### Register Write

```
Byte 0-1: CAN ID (low byte, high byte)
Byte 2:   0x55 (write command)
Byte 3:   Register ID (RID)
Byte 4-7: Register value (4 bytes, format depends on register type)
```

#### Store Parameters

```
Byte 0-1: CAN ID (low byte, high byte)
Byte 2:   0xAA (store command)
Byte 3:   Register ID (RID) - typically 0x00 for all registers
Byte 4-7: Don't care (0x00)
```

### 4. Feedback Messages

Motors continuously send feedback messages with their current state:

- **Arbitration ID**: `feedback_id` (MST_ID, register 7)
- **Data Format**: 8 bytes encoding motor state

```
Byte 0:   Status (4 bits) | Motor ID (4 bits)
Byte 1-2: Position (16-bit, mapped to motor's position range)
Byte 3-4: Velocity (12-bit, mapped to motor's velocity range)
Byte 5:   Torque (12-bit, mapped to motor's torque range)
Byte 6:   MOSFET temperature (°C)
Byte 7:   Rotor temperature (°C)
```

#### Status Codes

| Code | Name | Description |
|------|------|-------------|
| 0 | DISABLED | Motor is disabled |
| 1 | ENABLED | Motor is enabled and ready |
| 2 | ERROR | Motor error state |
| 3 | RESERVED | Reserved |

### 5. Register Reply Messages

When a register is read, the motor responds with:

- **Arbitration ID**: `feedback_id` (MST_ID)
- **Data Format**: 8 bytes

```
Byte 0-2: CAN ID encoding
Byte 3:   Register ID (RID)
Byte 4-7: Register value (4 bytes, format depends on register type)
```

## Data Encoding

### Position/Velocity/Torque Encoding

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

### Stiffness/Damping Encoding

Stiffness (kp) and damping (kd) use fixed ranges:

- **Stiffness**: 0-500 (12-bit encoding)
- **Damping**: 0-5 (12-bit encoding)

## Message Timing

### Command Frequency

- **Recommended**: 100-1000 Hz
- **Minimum**: ~10 Hz (for basic control)
- **Maximum**: Limited by CAN bus bandwidth

### Feedback Frequency

- Motors send feedback automatically
- Typical frequency: 100-1000 Hz (depends on motor firmware)
- Feedback is asynchronous (not tied to command timing)

### Register Operations

- Register reads/writes are request-reply operations
- Typical timeout: 100-500 ms
- Store operations may take longer (flash write)

## Multi-Motor Communication

Multiple motors can share the same CAN bus:

1. Each motor has a unique `motor_id` (ESC_ID, register 8)
2. Each motor has a unique `feedback_id` (MST_ID, register 7)
3. Commands are addressed to specific `motor_id`
4. Feedback is identified by `feedback_id`

### Example: Three Motors

```
Motor 1: motor_id=0x01, feedback_id=0x11
Motor 2: motor_id=0x02, feedback_id=0x12
Motor 3: motor_id=0x03, feedback_id=0x13

MIT commands:
  Motor 1: arbitration_id = 0x001
  Motor 2: arbitration_id = 0x002
  Motor 3: arbitration_id = 0x003

Feedback:
  Motor 1: arbitration_id = 0x011
  Motor 2: arbitration_id = 0x012
  Motor 3: arbitration_id = 0x013
```

## Error Handling

### Timeout Protection

- Register operations have timeout protection
- If no reply received within timeout, operation fails
- Motor has CAN timeout alarm (register 9) - motor disables if no commands received

### Error States

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
- See [API Reference](../api/motor.md) for implementation details

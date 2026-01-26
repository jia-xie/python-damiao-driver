---
tags:
  - hardware
  - setup
  - wiring
---

# Motor Connection

This guide covers the physical connection of DaMiao motors to your system.

## Overview

DaMiao motors connect to your computer via CAN bus. This requires:

1. **CAN interface hardware** (USB-CAN adapter, CAN-capable board, etc.)
2. **CAN bus wiring** (CAN_H, CAN_L, GND)
3. **Termination resistors** (120Ω at both ends)
4. **Power supply** for the motors

## CAN Interface Options

### USB-CAN Adapters

Common USB-CAN adapters that work with SocketCAN:

- **CANable/CandleLight**: Open-source USB-CAN adapter
- **Peak PCAN-USB**: Commercial adapter with good Linux support
- **ZLG USBCAN**: Various models with SocketCAN drivers
- **IXXAT USB-to-CAN**: Professional-grade adapters

### Embedded Boards

Many embedded boards have built-in CAN interfaces:

- **Raspberry Pi**: With CAN HAT (e.g., Waveshare CAN HAT)
- **BeagleBone**: Built-in CAN interfaces
- **Jetson**: With CAN expansion boards
- **STM32/ESP32**: With CAN transceivers

### Requirements

- **SocketCAN support**: Must have Linux kernel driver
- **1 Mbps capability**: Should support 1 Mbps bitrate
- **Proper drivers**: May need to install kernel modules

## Wiring

### CAN Bus Wiring

CAN bus uses three wires:

| Wire | Description |
|------|-------------|
| CAN_H | CAN High signal |
| CAN_L | CAN Low signal |
| GND | Ground |

### Connection Diagram

```
[Computer/CAN Interface]
    |
    | CAN_H ────────────────┐
    | CAN_L ───────────────┤
    | GND ─────────────────┤
    |                      │
    |                  [Motor 1]
    |                      │
    | CAN_H ───────────────┤
    | CAN_L ───────────────┤
    | GND ─────────────────┤
    |                      │
    |                  [Motor 2]
    |                      │
    | CAN_H ───────────────┤
    | CAN_L ───────────────┤
    | GND ─────────────────┤
    |                      │
    |                  [Motor 3]
    |                      │
    |                  120Ω (Termination)
```

### Termination Resistors

**Critical**: Termination resistors (120Ω) must be installed at **both ends** of the bus.

- **Location**: First and last device on the bus
- **Value**: 120Ω (standard CAN bus impedance)
- **Type**: Standard resistor, can be through-hole or SMD
- **Connection**: Between CAN_H and CAN_L

Without termination resistors, signal reflections will cause communication errors.

### Power Supply

Motors require a separate power supply:

- **Voltage**: Check motor specifications (typically 24V or 48V)
- **Current**: Must supply enough current for all motors
- **Ground**: Connect motor power ground to CAN bus ground

!!! warning "Power Safety"
    - Ensure power supply matches motor voltage rating
    - Use appropriate fuses/circuit breakers
    - Verify polarity before connecting
    - Keep power and signal grounds connected

## Motor ID Configuration

Each motor on the bus must have a unique ID:

- **ESC_ID (Register 8)**: Motor receive ID (for commands)
- **MST_ID (Register 7)**: Motor feedback ID (for feedback messages)

### Default IDs

Motors typically come with default IDs. Check motor documentation or use the scan command:

```bash
# Motor type is optional (defaults to 4310)
damiao scan
```

### Changing Motor IDs

Use the CLI to change motor IDs:

```bash
# Change receive ID (ESC_ID)
damiao set-motor-id --current 1 --target 2 --motor-type 4340

# Change feedback ID (MST_ID)
damiao set-feedback-id --current 1 --target 3 --motor-type 4340
```

!!! note "ID Uniqueness"
    - Each motor must have a unique ESC_ID and MST_ID
    - IDs can be the same (e.g., both 0x01) but this is not recommended
    - Use sequential IDs for simplicity (0x01, 0x02, 0x03, ...)

## Multi-Motor Setup

### Bus Topology

For multiple motors:

1. Connect all motors in parallel on the CAN bus
2. Install termination resistors at both ends
3. Assign unique IDs to each motor
4. Use the same bitrate for all devices

### Example: Three Motors

```
Motor 1: ESC_ID=0x01, MST_ID=0x11
Motor 2: ESC_ID=0x02, MST_ID=0x12
Motor 3: ESC_ID=0x03, MST_ID=0x13
```

### Power Considerations

- **Total current**: Sum of all motor currents
- **Voltage drop**: Longer bus may have voltage drop
- **Power distribution**: Consider power distribution if motors are far apart

## Testing Connections

### 1. Verify CAN Interface

```bash
# Check interface is up
ip link show can0

# Should show: state UP
```

### 2. Scan for Motors

```bash
# Scan for connected motors (motor-type is optional)
damiao scan

# Should detect all connected motors
```

### 3. Test Communication

```bash
# Send zero command to verify communication
damiao set-zero-command --id 1 --motor-type 4340
```

### 4. Monitor CAN Traffic

```bash
# Install can-utils if needed
sudo apt-get install can-utils

# Monitor all CAN messages
candump can0
```

## Troubleshooting

### No Motors Detected

- **Check power**: Verify motors are powered on
- **Check wiring**: Verify CAN_H, CAN_L, GND connections
- **Check termination**: Verify 120Ω resistors are installed
- **Check bitrate**: Verify bitrate matches motor configuration
- **Check IDs**: Verify motor IDs are in scan range

### Intermittent Communication

- **Loose connections**: Check all connections are secure
- **Cable quality**: Verify cable is suitable for CAN bus
- **Bus length**: Keep bus length reasonable (< 40m for 1 Mbps)
- **Termination**: Verify termination resistors are correct

### Communication Errors

- **Bitrate mismatch**: All devices must use same bitrate
- **ID conflicts**: Each motor must have unique IDs
- **Bus errors**: Check for physical layer issues
- **Power issues**: Verify power supply is adequate

### Motor Not Responding

- **Enable motor**: Use `enable_all()` or enable command
- **Check status**: Read motor status from feedback
- **Clear errors**: Use clear error command if motor in error state
- **Verify mode**: Ensure control mode matches command type

## Safety Considerations

!!! warning "Safety First"
    - Always ensure motors are securely mounted before powering on
    - Keep clear of moving parts during testing
    - Use low values initially to verify motor response
    - Have emergency stop mechanism available
    - Test in safe environment before production use

## Further Reading

- [CAN Setup](can-set-up.md) - Software configuration
- [Communication Protocol](../concept/communication-protocol.md) - Protocol details
- [Motor Control Modes](../concept/motor-control-modes.md) - Control mode information

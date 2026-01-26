---
tags:
  - concept
  - can
  - hardware
---

# CAN Bus Fundamentals

This document explains the CAN (Controller Area Network) bus fundamentals as they relate to DaMiao motors.

## What is CAN Bus?

CAN bus is a robust, multi-master communication protocol designed for real-time control applications. It's widely used in automotive and industrial automation systems, including robotics.

## Why CAN for Motors?

CAN bus is ideal for motor control because:

- **Reliability**: Built-in error detection and fault tolerance
- **Real-time**: Deterministic message delivery with priority-based arbitration
- **Multi-device**: Multiple motors can share a single bus
- **Noise immunity**: Differential signaling resists electrical interference
- **Standardized**: Well-established protocol with broad hardware support

## CAN Bus Basics

### Physical Layer

- **Differential signaling**: Two wires (CAN_H and CAN_L) carry complementary signals
- **Termination**: 120Ω resistors required at both ends of the bus
- **Bitrate**: Configurable (typically 1 Mbps for DaMiao motors)
- **Topology**: Linear bus (all devices connected in parallel)

### Message Format

CAN messages consist of:

- **Arbitration ID**: 11-bit identifier (0x000-0x7FF) that determines message priority
- **Data**: Up to 8 bytes of payload
- **Control bits**: DLC (Data Length Code), RTR (Remote Transmission Request), etc.

### Arbitration

When multiple devices transmit simultaneously:

- Lower arbitration IDs have higher priority
- Devices with lower priority automatically back off
- No data is lost during arbitration
- Winner transmits immediately

## DaMiao Motor CAN Configuration

### Bitrate

DaMiao motors typically use **1 Mbps** (1,000,000 bits per second). The bitrate must match between all devices on the bus.

### Arbitration IDs

DaMiao motors use different arbitration IDs for different purposes:

| Purpose | Arbitration ID Format | Example (motor_id=1) |
|---------|----------------------|---------------------|
| MIT Control | `motor_id` | 0x001 |
| POS_VEL Control | `0x100 + motor_id` | 0x101 |
| VEL Control | `0x200 + motor_id` | 0x201 |
| FORCE_POS Control | `0x300 + motor_id` | 0x301 |
| Register Operations | `0x7FF` | 0x7FF |
| Feedback | `feedback_id` (MST_ID) | Variable |

### Message Length

All DaMiao motor messages are **8 bytes** (standard CAN frame length).

## SocketCAN on Linux

The driver uses SocketCAN, the Linux CAN subsystem:

- **Interface naming**: `can0`, `can1`, etc.
- **Configuration**: Standard Linux network tools (`ip link`)
- **Access**: Standard socket API

### Basic Setup

```bash
# Bring up CAN interface
sudo ip link set can0 up type can bitrate 1000000

# Check status
ip link show can0

# Monitor traffic
candump can0
```

## Bus Topology

```
[Computer] ----[CAN Interface]----[CAN Bus]----[Motor 1]
                                              [Motor 2]
                                              [Motor 3]
```

### Requirements

- **Termination resistors**: 120Ω at both ends of the bus
- **Bitrate matching**: All devices must use the same bitrate
- **Proper wiring**: CAN_H and CAN_L must be connected correctly

## Error Handling

CAN bus includes built-in error detection:

- **CRC (Cyclic Redundancy Check)**: Detects transmission errors
- **ACK (Acknowledgment)**: Confirms successful reception
- **Error frames**: Automatically transmitted on error detection
- **Bus-off**: Device disconnects after repeated errors

## Best Practices

1. **Termination**: Always use 120Ω resistors at both bus ends
2. **Bitrate**: Verify all devices use the same bitrate
3. **Cable length**: Keep bus length reasonable (< 40m for 1 Mbps)
4. **Grounding**: Ensure proper ground connections
5. **Shielding**: Use shielded cables in noisy environments

## Troubleshooting

### No Communication

- Check CAN interface is up: `ip link show can0`
- Verify bitrate matches motor configuration
- Check termination resistors are present
- Verify motor is powered on

### Intermittent Communication

- Check for loose connections
- Verify cable quality and length
- Check for electrical interference
- Verify termination resistors

### Error Messages

- **Error Code 105**: No buffer space - motor not responding or not powered
- **Timeout errors**: Motor not receiving commands or not responding
- **Bus errors**: Physical layer issues (wiring, termination, bitrate mismatch)

## Further Reading

- [SocketCAN Documentation](https://www.kernel.org/doc/html/latest/networking/can.html)
- [CAN-utils Documentation](https://github.com/linux-can/can-utils)

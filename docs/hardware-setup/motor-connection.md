---
tags:
  - hardware
  - setup
  - wiring
---

# Motor Connection

This guide covers the physical connection of DaMiao motors to your system.

For CAN interface bring-up and software configuration, see [CAN Setup](can-set-up.md).

## Wiring

CAN bus uses two wires:

| Wire | Description |
|------|-------------|
| CAN_H | CAN High signal |
| CAN_L | CAN Low signal |


![CAN bus motor connection diagram with CAN interface, three motors, and 120Ω termination at both ends](motor-connection-diagram.svg){ .doc-screenshot }

For CAN bus termination requirements, see [Termination Resistors](can-set-up.md#termination-resistors).

## Power

Motors require a separate power supply:

- **Voltage**: Check motor specifications (typically 24V or 48V)
- **Current**: Must supply enough current for all motors

!!! warning "Power Safety"
    - Ensure power supply matches motor voltage rating
    - Use appropriate fuses/circuit breakers
    - Verify polarity before connecting
    - Keep power and signal grounds connected

Power planning:

- **Total current**: Sum of all motor currents
- **Voltage drop**: Longer bus may have voltage drop
- **Power distribution**: Consider distribution if motors are far apart

## Connection Bring-Up and Validation

Use one of the following workflows to validate your setup:

- **GUI (recommended)**: [Web GUI - Connection Bring-Up Workflow](../package-usage/web-gui.md#connection-bring-up-workflow-gui)
- **CLI (headless)**: [CLI Tool - Connection Bring-Up Workflow](../package-usage/cli-tool.md#connection-bring-up-workflow-headless)

## Troubleshooting

| Symptom | Checks |
|---------|--------|
| No motors detected | Verify power is on.<br>Verify CAN_H / CAN_L / GND wiring.<br>Verify 120 ohm termination on both ends.<br>Verify bitrate matches motor configuration.<br>Verify motor IDs are in scan range. |
| Intermittent communication | Check loose connections.<br>Check cable quality for CAN use.<br>Keep bus length reasonable (< 40 m at 1 Mbps).<br>Verify termination values and placement. |
| Communication errors | Verify all devices use the same bitrate.<br>Resolve motor ID conflicts.<br>Check physical-layer bus errors.<br>Verify power supply capacity/stability. |
| Motor not responding | Enable the motor in control flow.<br>Check status feedback.<br>Clear errors if motor is in fault state.<br>Verify [control mode](../concept/motor-control-modes.md) matches the command type. |

## Safety

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
- [Web GUI](../package-usage/web-gui.md) - Recommended for understanding control modes interactively with `damiao gui`

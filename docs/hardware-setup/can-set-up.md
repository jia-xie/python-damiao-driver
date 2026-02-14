---
tags:
  - hardware
  - setup
  - can
---

# CAN Setup

This guide covers setting up the CAN interface for use with DaMiao motors.

## Prerequisites

- Linux operating system
- CAN interface hardware (USB-CAN adapter, CAN-capable board, etc.)
- SocketCAN drivers
- Jetson: [NVIDIA Jetson Linux CAN guide](https://docs.nvidia.com/jetson/archives/r35.3.1/DeveloperGuide/text/HR/ControllerAreaNetworkCan.html)

## Termination Resistors

**Critical**: Termination resistors (120 ohms) must be installed at **both ends** of the bus.

- **Location**: First and last device on the bus
- **Value**: 120 ohms (standard CAN bus impedance)
- **Type**: Standard resistor, can be through-hole or SMD
- **Connection**: Between CAN_H and CAN_L

Without termination resistors, signal reflections will cause communication errors.

!!! note
    Some CAN devices (for example USB2CAN adapters and DaMiao Motor 3507) have a termination resistor switch to engage onboard resistors.

## Basic CAN Setup

**Step 1 - Check CAN interface**

List available network interfaces:

```bash
ip link show
```

Look for `can0`, `can1`, or similar interfaces.

**Step 2 - Bring up CAN interface**

```bash
sudo ip link set can0 up type can bitrate 1000000
```

This sets up `can0` with a 1 Mbps bitrate.

**Step 3 - Verify interface state**

```bash
ip link show can0
```

You should see the interface is `UP`.

## Persistent Interface Name (Fixed Device Name)

If you use multiple CAN adapters, Linux may swap `can0`/`can1` order across reboots.  
Use a udev rule to assign a fixed name to a specific adapter.

**Step 1 - Find a unique identifier**

```bash
# Replace can0 with your current interface
udevadm info -a -p /sys/class/net/can0 | grep -E "ATTRS\\{serial\\}|ATTRS\\{idVendor\\}|ATTRS\\{idProduct\\}"
```

Pick a stable value such as `ATTRS{serial}`.

**Step 2 - Create a udev rule**

```bash
sudo tee /etc/udev/rules.d/70-can-persistent.rules >/dev/null <<'EOF'
SUBSYSTEM=="net", ACTION=="add", KERNEL=="can*", ATTRS{serial}=="YOUR_SERIAL_HERE", NAME="can_damiao"
EOF
```

Notes:

- Replace `YOUR_SERIAL_HERE` with your adapter serial.
- `can_damiao` is an example; interface names must be 15 characters or fewer.

**Step 3 - Reload rules and reconnect adapter**

```bash
sudo udevadm control --reload-rules
```

Then unplug/replug the adapter (or reboot).

**Step 4 - Use the fixed name**

```bash
sudo ip link set can_damiao up type can bitrate 1000000
damiao scan --channel can_damiao
```

## Testing

**Using `candump`**

```bash
sudo apt-get install can-utils
sudo candump can0
```

This will show all CAN messages on the bus.

**Using `damiao scan`**

```bash
damiao scan --channel can0
```

## Troubleshooting

| Symptom | Checks / Fix |
|---------|---------------|
| Interface not found | Check hardware connection.<br>Verify drivers are loaded: `lsmod \| grep can`.<br>Check kernel logs: `dmesg \| grep can`. |
| Permission errors | Run with `sudo` or add user to CAN-access group:<br>`sudo usermod -a -G dialout $USER`.<br>Log out and back in. |
| Bitrate mismatch | Ensure CAN bitrate matches motor firmware configuration. |

## Multiple CAN Interfaces

If you have multiple CAN interfaces:

```bash
sudo ip link set can0 up type can bitrate 1000000
sudo ip link set can1 up type can bitrate 1000000
```

Then specify the channel in your code:

```python
controller = DaMiaoController(channel="can1", bustype="socketcan")
```

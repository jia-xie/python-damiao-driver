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

## Basic CAN Setup

### 1. Check CAN Interface

List available network interfaces:

```bash
ip link show
```

Look for `can0`, `can1`, or similar interfaces.

### 2. Bring Up CAN Interface

```bash
sudo ip link set can0 up type can bitrate 1000000
```

This sets up `can0` with a 1 Mbps bitrate.

### 3. Verify Interface

```bash
ip link show can0
```

You should see the interface is `UP`.

## Persistent Interface Name (Fixed Device Name)

If you use multiple CAN adapters, Linux may swap `can0`/`can1` order across reboots.  
Use a udev rule to assign a fixed name to a specific adapter.

### 1. Find a Unique Identifier

```bash
# Replace can0 with your current interface
udevadm info -a -p /sys/class/net/can0 | grep -E "ATTRS\\{serial\\}|ATTRS\\{idVendor\\}|ATTRS\\{idProduct\\}"
```

Pick a stable value such as `ATTRS{serial}`.

### 2. Create a udev Rule

```bash
sudo tee /etc/udev/rules.d/70-can-persistent.rules >/dev/null <<'EOF'
SUBSYSTEM=="net", ACTION=="add", KERNEL=="can*", ATTRS{serial}=="YOUR_SERIAL_HERE", NAME="can_damiao"
EOF
```

Notes:

- Replace `YOUR_SERIAL_HERE` with your adapter serial.
- `can_damiao` is an example; interface names must be 15 characters or fewer.

### 3. Reload Rules and Reconnect Adapter

```bash
sudo udevadm control --reload-rules
```

Then unplug/replug the adapter (or reboot).

### 4. Use the Fixed Name

```bash
sudo ip link set can_damiao up type can bitrate 1000000
damiao scan --channel can_damiao
```

## Testing CAN Interface

### Using candump

```bash
sudo apt-get install can-utils
sudo candump can0
```

This will show all CAN messages on the bus.

### Using damiao scan

```bash
damiao scan --channel can0
```

## Troubleshooting

### Interface Not Found

- Check hardware connection
- Verify drivers are loaded: `lsmod | grep can`
- Check dmesg for errors: `dmesg | grep can`

### Permission Errors

You may need to run with `sudo` or add your user to a group with CAN access:

```bash
sudo usermod -a -G dialout $USER
```

Then log out and back in.

### Bitrate Mismatch

Ensure the CAN bitrate matches your motor configuration. Check motor firmware settings.

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

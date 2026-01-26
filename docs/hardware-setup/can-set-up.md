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

## Testing CAN Interface

### Using candump

```bash
sudo apt-get install can-utils
sudo candump can0
```

This will show all CAN messages on the bus.

### Using damiao scan

```bash
# Motor type is optional (defaults to 4310)
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
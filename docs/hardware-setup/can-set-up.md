---
tags:
  - hardware
  - setup
  - can
---

# CAN Setup

This guide covers setting up the CAN interface for use with DaMiao motors on Linux (SocketCAN) and macOS (gs_usb).

## Tested Hardware

| Device | Interface | Linux | macOS | Serial Number per Unit | Notes |
|--------|-----------|-------|-------|------------------------|-------|
| [i2rt USB2CAN](https://i2rt.com/products/usb-to-can-converter) | socketcan (Linux) / gs_usb (macOS) | ✅ | ✅ | ✅ | socketcan on Linux; gs_usb on macOS |
| CANable 2.0 (Amazon) | socketcan (Linux) / gs_usb (macOS) | ✅ | ✅ | ✅ | candleLight firmware; use index `"0"` or serial number |

## Termination Resistors

**Critical**: Termination resistors (120 ohms) must be installed at **both ends** of the bus.

- **Location**: First and last device on the bus
- **Value**: 120 ohms (standard CAN bus impedance)
- **Type**: Standard resistor, can be through-hole or SMD
- **Connection**: Between CAN_H and CAN_L

Without termination resistors, signal reflections will cause communication errors.

!!! note
    Some CAN devices (for example USB2CAN adapters and DaMiao Motor 3507) have a termination resistor switch to engage onboard resistors.

---

## Linux — SocketCAN Setup

### Prerequisites

- Linux operating system
- CAN interface hardware (USB-CAN adapter, CAN-capable board, etc.)
- SocketCAN drivers
- Jetson: [NVIDIA Jetson Linux CAN guide](https://docs.nvidia.com/jetson/archives/r35.3.1/DeveloperGuide/text/HR/ControllerAreaNetworkCan.html)

### Basic Setup

**Step 1 — Check CAN interface**

```bash
ip link show
```

Look for `can0`, `can1`, or similar interfaces.

**Step 2 — Bring up CAN interface**

```bash
sudo ip link set can0 up type can bitrate 1000000
```

**Step 3 — Verify interface state**

```bash
ip link show can0
```

You should see the interface is `UP`.

### Persistent Interface Name (Fixed Device Name)

If you use multiple CAN adapters, Linux may swap `can0`/`can1` order across reboots.
Use a udev rule to assign a fixed name to a specific adapter.

**Step 1 — Find a unique identifier**

```bash
# Replace can0 with your current interface
udevadm info -a -p /sys/class/net/can0 | grep -E "ATTRS\{serial\}|ATTRS\{idVendor\}|ATTRS\{idProduct\}"
```

Pick a stable value such as `ATTRS{serial}`.

**Step 2 — Create a udev rule**

```bash
sudo tee /etc/udev/rules.d/70-can-persistent.rules >/dev/null <<'EOF'
SUBSYSTEM=="net", ACTION=="add", KERNEL=="can*", ATTRS{serial}=="YOUR_SERIAL_HERE", NAME="can_damiao"
EOF
```

Notes:

- Replace `YOUR_SERIAL_HERE` with your adapter serial.
- `can_damiao` is an example; interface names must be 15 characters or fewer.
- To distinguish two identical adapters without unique serials, match by USB port path using `KERNELS=="1-1.2.1"` instead.

**Step 3 — Reload rules and reconnect adapter**

```bash
sudo udevadm control --reload-rules
```

Then unplug/replug the adapter (or reboot).

**Step 4 — Use the fixed name**

```bash
sudo ip link set can_damiao up type can bitrate 1000000
damiao scan --channel can_damiao
```

### Multiple CAN Interfaces

```bash
sudo ip link set can0 up type can bitrate 1000000
sudo ip link set can1 up type can bitrate 1000000
```

```python
controller_l = DaMiaoController(channel="can_follow_l", bustype="socketcan")
controller_r = DaMiaoController(channel="can_follow_r", bustype="socketcan")
```

---

## macOS — gs_usb Setup

### Prerequisites

- macOS with a gs_usb-compatible USB-CAN adapter (CANable, candleLight, etc.)
- `gs_usb` and `pyusb` are installed automatically with `pip install damiao-motor` on macOS — no extra flags needed.

### Basic Setup

No OS-level interface configuration is needed. The adapter is opened directly via libusb.

**Step 1 — List connected devices**

```bash
python -c "
from gs_usb.gs_usb import GsUsb
for i, d in enumerate(GsUsb.scan()):
    print(i, d.serial_number, d.gs_usb.port_numbers)
"
```

Example output:

```
0 0046002E594E501820313332 (1, 1)
1 0046002E594E501820313333 (1, 2)
```

Each row shows: `<index> <serial_number> <port_numbers>`

**Step 2 — Connect in Python**

By index (first detected device):

```python
controller = DaMiaoController(channel="0", bustype="gs_usb", bitrate=1_000_000)
```

By serial number (stable across replugs, recommended if unique serials are present):

```python
controller = DaMiaoController(channel="ABCD1234", bustype="gs_usb", bitrate=1_000_000)
```

### Identifying Adapters Without Unique Serials

Many cheap CANable clones have no serial number (`None`) or the same hardcoded value on every unit. In that case, identify by physical USB port — the `port_numbers` tuple stays stable as long as the cable is plugged into the same physical socket:

```python
from gs_usb.gs_usb import GsUsb

def find_gs_usb_index_by_port(port_path: tuple) -> int:
    devs = GsUsb.scan()
    for i, dev in enumerate(devs):
        if tuple(dev.gs_usb.port_numbers) == port_path:
            return i
    raise RuntimeError(f"No gs_usb device on port {port_path}")

# Plug adapters in and note their port_numbers from the scan above, then:
ctrl_l = DaMiaoController(channel=str(find_gs_usb_index_by_port((1, 2, 1))), bustype="gs_usb", bitrate=1_000_000)
ctrl_r = DaMiaoController(channel=str(find_gs_usb_index_by_port((1, 3, 2))), bustype="gs_usb", bitrate=1_000_000)
```

This is the macOS equivalent of Linux udev `KERNELS==` port-path matching.

---

## Testing

**Linux — using `candump`**

```bash
sudo apt-get install can-utils
sudo candump can0
```

**All platforms — using `damiao scan`**

```bash
# Linux
damiao scan --channel can0

# macOS
damiao scan --channel 0 --bustype gs_usb --bitrate 1000000
```

---

## Troubleshooting

| Symptom | Checks / Fix |
|---------|--------------|
| Interface not found (Linux) | Check hardware connection.<br>Verify drivers: `lsmod \| grep can`.<br>Check kernel logs: `dmesg \| grep can`. |
| Permission errors (Linux) | Run with `sudo` or add user to group:<br>`sudo usermod -a -G dialout $USER`. Log out and back in. |
| Device not found (macOS) | Run `python -c "from gs_usb.gs_usb import GsUsb; print(GsUsb.scan())"` to verify pyusb sees the adapter.<br>Try a different USB port or cable. |
| Reconnect fails (macOS) | Ensure `damiao-motor` was installed on macOS so that `gs_usb` and `pyusb` were pulled in automatically. |
| Bitrate mismatch | Ensure CAN bitrate matches motor firmware configuration. |

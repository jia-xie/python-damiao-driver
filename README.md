# damiao-motor

![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue)
![Platform](https://img.shields.io/badge/platform-Linux-lightgrey)
[![PyPI](https://img.shields.io/badge/pypi-damiao--motor-blue)](https://pypi.org/project/damiao-motor/)

<img src="docs/package-usage/gui-screenshot.png" alt="DaMiao Motor Control GUI" width="1000">

Python driver for **DaMiao** brushless motors over CAN with a unified CLI, web GUI, and library API.

- **Control modes:** MIT, POS_VEL, VEL, FORCE_POS  
- **Motor types:** 3507, 4310, 4340, 6006, 8006, 8009, 10010/L, and more  
- **Tools:** `damiao` CLI (scan, send-cmd-mit, send-cmd-pos-vel, send-cmd-vel, send-cmd-force-pos, set-zero-command, set-motor-id, gui, etc.) with unified interface  

**Docs:** [GitHub Pages](https://jia-xie.github.io/python-damiao-driver/) · **Firmware:** [DaMiao motor firmware (Gitee)](https://gitee.com/kit-miao/motor-firmware)

---

## Installation

```bash
pip install damiao-motor
```

**Requirements:** Linux, CAN interface (e.g. socketcan on `can0`). Bring the interface up and set bitrate to match the motor (e.g. 1 Mbps) before use.

---

## Quick start

**Safety:** Examples move the motor. Mount it securely and keep clear of moving parts.

```bash
python examples/example.py
```

Edit `examples/example.py` to set `motor_id`, `feedback_id`, `motor_type`, and `channel` for your hardware.

### Minimal code

```python
from damiao_motor import DaMiaoController

controller = DaMiaoController(channel="can0", bustype="socketcan")
motor = controller.add_motor(motor_id=0x01, feedback_id=0x00, motor_type="4340")

controller.enable_all()
motor.ensure_control_mode("MIT")  # required before send_cmd_mit in MIT mode

motor.send_cmd_mit(target_position=1.0, target_velocity=0.0, stiffness=20.0, damping=0.5, feedforward_torque=0.0)
# ... controller polls feedback in background; use motor.get_states() to read

controller.shutdown()
```

---

## CLI: `damiao`

All `damiao` subcommands require `--motor-type` (e.g. `4340`). Use `damiao <cmd> --help` for options.

| Command | Description |
|---------|-------------|
| `damiao scan --motor-type 4340` | Scan for motors on the bus |
| `damiao send-cmd-mit --motor-type 4340 --id 1` | Send MIT control mode command |
| `damiao send-cmd-pos-vel --motor-type 4340 --id 1` | Send POS_VEL control mode command |
| `damiao send-cmd-vel --motor-type 4340 --id 1` | Send VEL control mode command |
| `damiao send-cmd-force-pos --motor-type 4340 --id 1` | Send FORCE_POS control mode command |
| `damiao set-zero-command --motor-type 4340 --id 1` | Send zero command (hold at zero) |
| `damiao set-zero-position --motor-type 4340 --id 1` | Set current position to zero |
| `damiao set-can-timeout --motor-type 4340 --id 1 --timeout-ms 1000` | Set CAN timeout (register 9) |
| `damiao set-motor-id` / `damiao set-feedback-id` | Change motor or feedback ID (registers 8, 7) |
| `damiao gui` | Launch web-based GUI for motor control |

---

## Web GUI: `damiao gui`

```bash
damiao gui
```

Then open **http://127.0.0.1:5000**.

The interface provides:

- **Connection & Motor Selection** — CAN channel, Connect/Disconnect, Scan for motors, choose motor by ID  
- **Motor Control** — Motor type, control mode (MIT, POS_VEL, VEL, FORCE_POS), target position/velocity/stiffness/damping/torque, Enable/Disable, Stop, Single/Continuous command, Set Zero, Clear Error  
- **Motor Feedback** — Live status, position, velocity, torque, MOSFET and rotor temperature  
- **Register Parameters** — Table of all registers with edit for writable ones  
- **Charts** — Real-time position, velocity, and torque vs. time with zoom, export, and axis controls  

---

## Library API

- **`DaMiaoController(channel, bustype)`** — owns the CAN bus and background feedback polling.  
- **`controller.add_motor(motor_id, feedback_id, motor_type)`** — add a motor. `motor_type` is required (e.g. `"4340"`).  
- **`motor.ensure_control_mode(mode)`** — set register 10 to `"MIT"`, `"POS_VEL"`, `"VEL"`, or `"FORCE_POS"` before sending commands in that mode.  
- **`motor.send_cmd_mit(...)`** — send MIT mode command (position, velocity, stiffness, damping, feedforward torque)
- **`motor.send_cmd_pos_vel(...)`** — send POS_VEL mode command (position, velocity)
- **`motor.send_cmd_vel(...)`** — send VEL mode command (velocity)
- **`motor.send_cmd_force_pos(...)`** — send FORCE_POS mode command (position, velocity_limit, current_limit)
- **`motor.send_cmd(...)`** — convenience wrapper that calls the appropriate method based on control_mode  
- **`motor.get_states()`** — last decoded feedback (pos, vel, torq, status, etc.).  
- **`motor.get_register` / `motor.write_register`** — read/write registers by ID.  

See the [API docs](https://jia-xie.github.io/python-damiao-driver/dev/api/controller/) for details.

---
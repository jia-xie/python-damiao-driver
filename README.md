## damiao-motor

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![Platform](https://img.shields.io/badge/platform-Linux-lightgrey)
[![Maintainer](https://img.shields.io/badge/maintainer-jia--xie-blue)](https://github.com/jia-xie)
[![PyPI](https://img.shields.io/badge/pypi-damiao--motor-blue)](https://pypi.org/project/damiao-motor/)

Python driver for DaMiao motors over CAN, with support for multiple motors on a single bus.

**Documentation:** [Full documentation available on GitHub Pages](https://jia-xie.github.io/python-damiao-driver/)

**Related Links:**
- [Motor Firmware Repository](https://gitee.com/kit-miao/motor-firmware) - Official DaMiao motor firmware

### Installation

```bash
pip install damiao-motor
```


The package provides two command-line tools:

- **`damiao-scan`**: Scan for connected motors on the CAN bus
  ```bash
  damiao-scan
  damiao-scan --ids 1 2 3 --debug
  ```

- **`damiao-gui`**: Web-based GUI for viewing and editing motor parameters
  ```bash
  damiao-gui
  # Then open http://127.0.0.1:5000 in your browser
  ```

  **GUI Interface:**
  
  <img src="https://raw.githubusercontent.com/jia-xie/python-damiao-driver/main/docs/gui-screenshot.png" alt="DaMiao Motor Parameter Editor GUI" width="400">
  
  The web interface allows you to:
  - Scan for motors
  - View all register parameters in a table
  - Edit writable parameters

### Quick usage

**Safety note:** The examples below will move the motor. Make sure the motor is securely mounted, keep clear of moving parts, and follow your lab/robot safety guidelines.

Single/multi-motor examples are in the `examples/` directory. After installation you can run, for example:

```bash
python examples/multi_motor.py
```

Adjust motor IDs and gains in the example scripts to match your hardware.

A minimal single-motor example using the library API:

```python
import math
import time
from damiao_motor import DaMiaoController

controller = DaMiaoController(channel="can0", bustype="socketcan")
motor = controller.add_motor(motor_id=0x01, feedback_id=0x00)

controller.enable_all()
time.sleep(0.1)

# Control loop - feedback is automatically polled in background
try:
    while True:
        target_pos = 1.0 * math.sin(2.0 * math.pi * 0.2 * time.time())
        motor.send_cmd(target_position=target_pos, target_velocity=0.0, stiffness=20.0, damping=0.5, feedforward_torque=0.0)
        # Access feedback (automatically updated in background)
        states = motor.get_states()
        if states:
            print(f"pos={states.get('pos'):.3f}, vel={states.get('vel'):.3f}")
        time.sleep(0.01)
except KeyboardInterrupt:
    controller.shutdown()
```
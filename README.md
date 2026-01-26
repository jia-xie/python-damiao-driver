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

**Safety note:** The example will move the motor. Ensure it is securely mounted and keep clear of moving parts.

```bash
python examples/example.py
```

Edit `examples/example.py` to change `motor_id`, `motor_type`, or `channel` (defaults: 0x01, DM4340, can0).
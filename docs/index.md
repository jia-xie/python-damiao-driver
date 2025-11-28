# DaMiao Motor Driver

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![Platform](https://img.shields.io/badge/platform-Linux-lightgrey)
[![PyPI](https://img.shields.io/badge/pypi-damiao--motor-blue)](https://pypi.org/project/damiao-motor/)

Python driver for DaMiao motors over CAN, with support for multiple motors on a single bus.

## Features

- ✅ **Multi-motor support** - Control multiple motors on a single CAN bus
- ✅ **MIT-style control** - Position, velocity, stiffness, damping, and feedforward torque control
- ✅ **Real-time feedback** - Automatic background polling of motor states
- ✅ **CLI tools** - Command-line utilities for scanning and configuration
- ✅ **Web GUI** - Browser-based interface for viewing and editing motor parameters
- ✅ **Easy to use** - Simple Python API for integration into your projects

## Quick Start

```bash
pip install damiao-motor
```

```python
from damiao_motor import DaMiaoController

controller = DaMiaoController(channel="can0", bustype="socketcan")
motor = controller.add_motor(motor_id=0x01, feedback_id=0x00)

controller.enable_all()
motor.send_cmd(target_position=1.0, target_velocity=0.0, stiffness=20.0, damping=0.5)
```

## Documentation

This documentation covers:

- **[Getting Started](getting-started/installation.md)** - Installation and setup
- **[API Reference](api/controller.md)** - Complete API documentation
- **[Configuration](configuration/can-setup.md)** - CAN bus and motor configuration

## Related Links

- [Motor Firmware Repository](https://gitee.com/kit-miao/motor-firmware) - Official DaMiao motor firmware
- [GitHub Repository](https://github.com/jia-xie/python-damiao-driver) - Source code and issues
- [PyPI Package](https://pypi.org/project/damiao-motor/) - Python package index

## Safety Warning

!!! warning "Safety First"
    Always ensure motors are securely mounted and operated in safe conditions. Keep clear of moving parts and follow your lab/robot safety guidelines.


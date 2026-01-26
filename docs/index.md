# DaMiao Motor Driver

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![Platform](https://img.shields.io/badge/platform-Linux-lightgrey)
[![PyPI](https://img.shields.io/badge/pypi-damiao--motor-blue)](https://pypi.org/project/damiao-motor/)

We created this Python driver because many people in the robot learning community use DaMiao motors, and we want to make using this excellent product as easy to use as possible.

## Features

- ✅ **CLI tools** - Command-line utilities for scanning and configuration
- ✅ **Web GUI** - Browser-based interface for viewing and editing motor parameters
- ✅ **Easy to use** - Simple Python API for integration into your projects

## Installation
### Install from PyPI
Install using `pip`
```bash
pip install damiao-motor
```
### Install from Source
To install from the source repository:

```bash
git clone https://github.com/jia-xie/python-damiao-driver.git
cd python-damiao-driver
pip install -e .
```

### Verify Installation

After installation, verify that the package is correctly installed:

```bash
python -c "import damiao_motor; print(damiao_motor.__version__)"
```

You should also be able to use the command-line tools:

```bash
damiao --help
damiao gui --help
```

## Quick Start
Minimal python script to control the motor

```python
from damiao_motor import DaMiaoController

controller = DaMiaoController(channel="can0", bustype="socketcan")
motor = controller.add_motor(motor_id=0x01, feedback_id=0x00, motor_type="4340")

controller.enable_all()
motor.send_cmd(target_position=1.0, target_velocity=0.0, stiffness=20.0, damping=0.5, feedforward_torque=0.0)
```

## Related Links

- [Motor Firmware Repository](https://gitee.com/kit-miao/motor-firmware) - Official DaMiao motor firmware
- [GitHub Repository](https://github.com/jia-xie/python-damiao-driver) - Source code and issues
- [PyPI Package](https://pypi.org/project/damiao-motor/) - Python package index

## Safety Warning

!!! warning "Safety First"
    Always ensure motors are securely mounted and operated in safe conditions. Keep clear of moving parts and follow your lab/robot safety guidelines.

## Next Steps

- [Guide](guide/hardware-setup.md) - Complete setup and concepts guide
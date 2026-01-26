---
tags:
  - getting-started
  - overview
---

# DaMiao Motor

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![Platform](https://img.shields.io/badge/platform-Linux-lightgrey)
[![PyPI](https://img.shields.io/badge/pypi-damiao--motor-blue)](https://pypi.org/project/damiao-motor/)

![DaMiao Motor Control Web GUI](package-usage/gui-screenshot.png)

## Features

- ✅ **[CLI tools](package-usage/cli-tool.md)** - Command-line utilities for easy motor control
- ✅ **[GUI](package-usage/web-gui.md)** - Browser-based interface for viewing and editing motor parameters
- ✅ **[Python API](api/motor.md)** - Simple API for integrating motor control into your Python projects

## Installation
### Install from PyPI
Install using `pip`
```bash
pip install damiao-motor
```
### Install from source for latest updates
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
```

## Next Steps

- [Hardware Setup](hardware-setup/can-set-up.md) - CAN interface setup
- [Package Usage](package-usage/cli-tool.md) - Using the CLI tools
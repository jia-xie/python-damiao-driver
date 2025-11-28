# Installation

## Requirements

- Python 3.8 or higher
- Linux operating system
- CAN interface (socketcan)

## Install from PyPI

The recommended way to install `damiao-motor` is using pip:

```bash
pip install damiao-motor
```

## Install from Source

To install from the source repository:

```bash
git clone https://github.com/jia-xie/python-damiao-driver.git
cd python-damiao-driver
pip install -e .
```

## Dependencies

The package automatically installs the following dependencies:

- `python-can>=4.3,<5.0` - CAN bus communication
- `flask>=3.0,<4.0` - Web GUI server

## Verify Installation

After installation, verify that the package is correctly installed:

```bash
python -c "import damiao_motor; print(damiao_motor.__version__)"
```

You should also be able to use the command-line tools:

```bash
damiao-scan --help
damiao-gui --help
```

## Next Steps

- [Quick Start Guide](quick-start.md) - Get up and running quickly
- [CAN Setup](../configuration/can-setup.md) - Configure your CAN interface


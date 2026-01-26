---
tags:
  - api
  - reference
  - registers
---

# Registers

This page documents all motor registers available in the DaMiao motor.

## RegisterInfo

::: damiao_motor.core.motor.RegisterInfo

## Register Table

### Protection and Basic Parameters

| ID | Variable | Description | Access | Range | Type |
|----|----------|-------------|--------|-------|------|
| 0 | `UV_Value` | Under-voltage protection value | RW | (10.0, 3.4E38] | float |
| 1 | `KT_Value` | Torque coefficient | RW | [0.0, 3.4E38] | float |
| 2 | `OT_Value` | Over-temperature protection value | RW | [80.0, 200) | float |
| 3 | `OC_Value` | Over-current protection value | RW | (0.0, 1.0) | float |
| 4 | `ACC` | Acceleration | RW | (0.0, 3.4E38) | float |
| 5 | `DEC` | Deceleration | RW | [-3.4E38, 0.0) | float |
| 6 | `MAX_SPD` | Maximum speed | RW | (0.0, 3.4E38] | float |

### System Identification and Configuration

| ID | Variable | Description | Access | Range | Type |
|----|----------|-------------|--------|-------|------|
| 7 | `MST_ID` | Feedback ID | RW | [0, 0x7FF] | uint32 |
| 8 | `ESC_ID` | Receive ID | RW | [0, 0x7FF] | uint32 |
| 9 | `TIMEOUT` | Timeout alarm time | RW | [0, 2^32-1] | uint32 |
| 10 | `CTRL_MODE` | Control mode | RW | [1, 4] | uint32 |

### Motor Physical Parameters (Read Only)

| ID | Variable | Description | Access | Range | Type |
|----|----------|-------------|--------|-------|------|
| 11 | `Damp` | Motor viscous damping coefficient | RO | / | float |
| 12 | `Inertia` | Motor moment of inertia | RO | / | float |
| 13 | `hw_ver` | Reserved | RO | / | uint32 |
| 14 | `sw_ver` | Software version number | RO | / | uint32 |
| 15 | `SN` | Reserved | RO | / | uint32 |
| 16 | `NPP` | Motor pole pairs | RO | / | uint32 |
| 17 | `Rs` | Motor phase resistance | RO | / | float |
| 18 | `Ls` | Motor phase inductance | RO | / | float |
| 19 | `Flux` | Motor flux linkage value | RO | / | float |
| 20 | `Gr` | Gear reduction ratio | RO | / | float |

### Mapping Ranges

| ID | Variable | Description | Access | Range | Type |
|----|----------|-------------|--------|-------|------|
| 21 | `PMAX` | Position mapping range | RW | (0.0, 3.4E38] | float |
| 22 | `VMAX` | Speed mapping range | RW | (0.0, 3.4E38] | float |
| 23 | `TMAX` | Torque mapping range | RW | (0.0, 3.4E38] | float |

### Control Loop Parameters

| ID | Variable | Description | Access | Range | Type |
|----|----------|-------------|--------|-------|------|
| 24 | `I_BW` | Current loop control bandwidth | RW | [100.0, 10000.0] | float |
| 25 | `KP_ASR` | Speed loop Kp | RW | [0.0, 3.4E38] | float |
| 26 | `KI_ASR` | Speed loop Ki | RW | [0.0, 3.4E38] | float |
| 27 | `KP_APR` | Position loop Kp | RW | [0.0, 3.4E38] | float |
| 28 | `KI_APR` | Position loop Ki | RW | [0.0, 3.4E38] | float |

### Protection and Efficiency

| ID | Variable | Description | Access | Range | Type |
|----|----------|-------------|--------|-------|------|
| 29 | `OV_Value` | Overvoltage protection value | RW | TBD | float |
| 30 | `GREF` | Gear torque efficiency | RW | (0.0, 1.0] | float |
| 31 | `Deta` | Speed loop damping coefficient | RW | [1.0, 30.0] | float |
| 32 | `V_BW` | Speed loop filter bandwidth | RW | (0.0, 500.0) | float |

### Enhancement Coefficients

| ID | Variable | Description | Access | Range | Type |
|----|----------|-------------|--------|-------|------|
| 33 | `IQ_c1` | Current loop enhancement coefficient | RW | [100.0, 10000.0] | float |
| 34 | `VL_c1` | Speed loop enhancement coefficient | RW | (0.0, 10000.0] | float |

### CAN and Version

| ID | Variable | Description | Access | Range | Type |
|----|----------|-------------|--------|-------|------|
| 35 | `can_br` | CAN baud rate code | RW | [0, 4] | uint32 |
| 36 | `sub_ver` | Sub-version number | RO | / | uint32 |

### Calibration Parameters (Read Only)

| ID | Variable | Description | Access | Range | Type |
|----|----------|-------------|--------|-------|------|
| 50 | `u_off` | U-phase offset | RO | - | float |
| 51 | `v_off` | V-phase offset | RO | - | float |
| 52 | `k1` | Compensation factor 1 | RO | - | float |
| 53 | `k2` | Compensation factor 2 | RO | - | float |
| 54 | `m_off` | Angle offset | RO | - | float |
| 55 | `dir` | Direction | RO | - | float |

### Position Feedback (Read Only)

| ID | Variable | Description | Access | Range | Type |
|----|----------|-------------|--------|-------|------|
| 80 | `p_m` | Motor position | RO | - | float |
| 81 | `xout` | Output shaft position | RO | - | float |

## CAN Baud Rate Codes

The `CAN_BAUD_RATE_CODES` dictionary maps baud rate codes to actual baud rates:

| Code | Baud Rate |
|------|-----------|
| 0 | 125,000 (125K) |
| 1 | 200,000 (200K) |
| 2 | 250,000 (250K) |
| 3 | 500,000 (500K) |
| 4 | 1,000,000 (1M) |

```python
from damiao_motor import CAN_BAUD_RATE_CODES

# Access baud rate codes
for code, baud_rate in CAN_BAUD_RATE_CODES.items():
    print(f"Code {code}: {baud_rate} bps")
```

## Usage Examples

### Reading Registers

```python
from damiao_motor import DaMiaoController

controller = DaMiaoController(channel="can0")
motor = controller.add_motor(motor_id=0x01, feedback_id=0x00, motor_type="4340")

# Read a specific register
value = motor.get_register(0x00)  # Read UV_Value

# Check if read was successful
if value is not None:
    print(f"Value: {value}")
```

### Writing Registers

```python
# Write to a register (only RW registers can be written)
success = motor.write_register(7, 0x01)  # Set MST_ID to 1

if success:
    print("Write successful")
else:
    print("Write failed")
```

### Accessing Register Information

```python
from damiao_motor import REGISTER_TABLE

# Access register information
for register_id, info in REGISTER_TABLE.items():
    print(f"Register {register_id:2d} (0x{register_id:02X}): "
          f"{info.variable:12s} - {info.description} "
          f"[{info.access}]")
```

## Safety Notes

!!! warning "Register Safety"
    - Some registers affect motor behavior immediately
    - Always verify register values before writing
    - Read-only (RO) registers cannot be written
    - Refer to motor firmware documentation for detailed register behavior
    - Test register changes in a safe environment

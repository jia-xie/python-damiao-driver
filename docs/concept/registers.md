---
tags:
  - concept
  - reference
  - registers
---

# Registers

This page documents all motor registers available in the DaMiao motor.

## How it works?
**Register Persistence (RAM vs Flash)**

When you write a register, it is applied immediately, but by default it is a runtime value (RAM).

- RAM write: takes effect now, but is lost after power cycle.
- Flash write: survives power cycle.

**Python API (`damiao_motor/core/motor.py`)**

Use these methods on `DaMiaoMotor`:

- `write_register(rid, value)` to write one register.
- Most `set_*` helper methods (for example `set_control_mode`, `set_speed_loop_kp`, `set_can_timeout`) internally call `write_register`.
- `store_parameters()` to save current parameters to flash.
- `set_can_baud_rate(...)` writes register `35` and then stores to flash automatically.

```python
# Write to register (RAM, immediate but NOT persistent)
motor.write_register(25, 20.0)  # KP_ASR

# Persist current parameters to flash
motor.store_parameters()
```

<span id="registers-web-gui"></span>
**Web GUI**

- Editing a register in the Web GUI writes it at runtime first.
- Click `Store Parameters` to write current parameters to flash.
- In current implementation, changing register `7` (`MST_ID`) or `8` (`ESC_ID`) also triggers a flash store automatically.

![Register Parameters – Description, Value, Type, Action; Edit with Save/Cancel for RW registers](../package-usage/screenshots/registers.png)

**CLI**

From current CLI implementation:

| Command | Register write | Flash persistence |
|---------|----------------|-------------------|
| `damiao set-motor-id` | Writes register `8` (`ESC_ID`) | Yes (calls `store_parameters()`) |
| `damiao set-feedback-id` | Writes register `7` (`MST_ID`) | Yes (calls `store_parameters()`) |
| `damiao set-can-timeout` | Writes register `9` (`TIMEOUT`) | Yes (calls `store_parameters()`) |

Other CLI control commands (`send-cmd-*`, `set-zero-command`, `set-zero-position`) do not store parameters to flash.

**CAN Baud Rate Codes**

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

**Usage Examples**

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

```python
# Write to a register (only RW registers can be written)
motor.write_register(7, 0x01)  # Set MST_ID to 1 (RAM)

# Keep the change after power cycle
motor.store_parameters()
```

```python
from damiao_motor import REGISTER_TABLE

# Access register information
for register_id, info in REGISTER_TABLE.items():
    print(f"Register {register_id:2d} (0x{register_id:02X}): "
          f"{info.variable:12s} - {info.description} "
          f"[{info.access}]")
```

**Safety Notes**

!!! warning "Register Safety"
    - Some registers affect motor behavior immediately
    - Always verify register values before writing
    - Read-only (RO) registers cannot be written
    - Refer to motor firmware documentation for detailed register behavior
    - Test register changes in a safe environment

## Register Table

| ID | Variable | Description | Access | Range | Type |
|----|----------|-------------|--------|-------|------|
| 0 | <span id="reg-0-uv-value"></span>`UV_Value` | Under-voltage protection value (see [UNDER_VOLTAGE `0x9`](communication-protocol.md#status-under-voltage)) | RW | (10.0, 3.4E38] | float |
| 1 | <span id="reg-1-kt-value"></span>`KT_Value` | Torque coefficient \(K_T\) used in [MIT mode](motor-control-modes.md#mit-mode) | RW | [0.0, 3.4E38] | float |
| 2 | <span id="reg-2-ot-value"></span>`OT_Value` | Over-temperature protection value (see [MOS/ROTOR over-temp](communication-protocol.md#status-over-temp)) | RW | [80.0, 200) | float |
| 3 | <span id="reg-3-oc-value"></span>`OC_Value` | Over-current protection value (see [OVER_CURRENT `0xA`](communication-protocol.md#status-over-current)) | RW | (0.0, 1.0) | float |
| 4 | `ACC` | Acceleration | RW | (0.0, 3.4E38) | float |
| 5 | `DEC` | Deceleration | RW | [-3.4E38, 0.0) | float |
| 6 | `MAX_SPD` | Maximum speed | RW | (0.0, 3.4E38] | float |

| ID | Variable | Description | Access | Range | Type |
|----|----------|-------------|--------|-------|------|
| 7 | `MST_ID` | Feedback ID | RW | [0, 0x7FF] | uint32 |
| 8 | `ESC_ID` | Receive ID | RW | [0, 0x7FF] | uint32 |
| 9 | <span id="reg-9-timeout"></span>`TIMEOUT` | Timeout alarm time (see [LOST_COMM `0xD`](communication-protocol.md#status-lost-comm)) | RW | [0, 2^32-1] | uint32 |
| 10 | `CTRL_MODE` | Control mode | RW | [1, 4] | uint32 |

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

| ID | Variable | Description | Access | Range | Type |
|----|----------|-------------|--------|-------|------|
| 21 | `PMAX` | Position mapping range | RW | (0.0, 3.4E38] | float |
| 22 | `VMAX` | Speed mapping range | RW | (0.0, 3.4E38] | float |
| 23 | `TMAX` | Torque mapping range | RW | (0.0, 3.4E38] | float |

<span id="pmax-vmax-tmax-defaults"></span>

!!! note "PMAX / VMAX / TMAX Defaults"
    Registers `21` (`PMAX`), `22` (`VMAX`), and `23` (`TMAX`) are writable and can be changed with register writes (API/CLI/GUI).

!!! warning "Recommended Practice"
    These mapping limits should normally stay at their default motor-type values.
    The SDK uses motor-type presets in `damiao_motor/core/motor.py` (`MOTOR_TYPE_PRESETS`, built from `_MOTOR_LIMIT_PARAM`) for command encoding and feedback decoding.
    If motor register mapping limits are changed without keeping SDK limits consistent, command/feedback scaling can become inconsistent.

**Default values in code (`_MOTOR_LIMIT_PARAM`):** 

| Motor type | PMAX | VMAX | TMAX |
|------------|------|------|------|
| `3507` | 12.566 | 50 | 5 |
| `4310` | 12.5 | 30 | 10 |
| `4310P` | 12.5 | 50 | 10 |
| `4340` | 12.5 | 10 | 28 |
| `4340P` | 12.5 | 10 | 28 |
| `6006` | 12.5 | 45 | 20 |
| `8006` | 12.5 | 45 | 40 |
| `8009` | 12.5 | 45 | 54 |
| `10010L` | 12.5 | 25 | 200 |
| `10010` | 12.5 | 20 | 200 |
| `H3510` | 12.5 | 280 | 1 |
| `G6215` | 12.5 | 45 | 10 |
| `H6220` | 12.5 | 45 | 10 |
| `JH11` | 12.5 | 10 | 12 |
| `6248P` | 12.566 | 20 | 120 |

| ID | Variable | Description | Access | Range | Type |
|----|----------|-------------|--------|-------|------|
| 24 | `I_BW` | Current loop control bandwidth | RW | [100.0, 10000.0] | float |
| 25 | <span id="reg-25-kp-asr"></span>`KP_ASR` | Speed loop Kp (used in [POS_VEL](motor-control-modes.md#pos-vel-mode), [VEL](motor-control-modes.md#vel-mode), [FORCE_POS](motor-control-modes.md#force-pos-mode)) | RW | [0.0, 3.4E38] | float |
| 26 | <span id="reg-26-ki-asr"></span>`KI_ASR` | Speed loop Ki (used in [POS_VEL](motor-control-modes.md#pos-vel-mode), [VEL](motor-control-modes.md#vel-mode), [FORCE_POS](motor-control-modes.md#force-pos-mode)) | RW | [0.0, 3.4E38] | float |
| 27 | <span id="reg-27-kp-apr"></span>`KP_APR` | Position loop Kp (used in [POS_VEL](motor-control-modes.md#pos-vel-mode), [FORCE_POS](motor-control-modes.md#force-pos-mode)) | RW | [0.0, 3.4E38] | float |
| 28 | <span id="reg-28-ki-apr"></span>`KI_APR` | Position loop Ki (used in [POS_VEL](motor-control-modes.md#pos-vel-mode), [FORCE_POS](motor-control-modes.md#force-pos-mode)) | RW | [0.0, 3.4E38] | float |

| ID | Variable | Description | Access | Range | Type |
|----|----------|-------------|--------|-------|------|
| 29 | <span id="reg-29-ov-value"></span>`OV_Value` | Overvoltage protection value (see [OVER_VOLTAGE `0x8`](communication-protocol.md#status-over-voltage)) | RW | TBD | float |
| 30 | `GREF` | Gear torque efficiency | RW | (0.0, 1.0] | float |
| 31 | `Deta` | Speed loop damping coefficient | RW | [1.0, 30.0] | float |
| 32 | `V_BW` | Speed loop filter bandwidth | RW | (0.0, 500.0) | float |

| ID | Variable | Description | Access | Range | Type |
|----|----------|-------------|--------|-------|------|
| 33 | `IQ_c1` | Current loop enhancement coefficient | RW | [100.0, 10000.0] | float |
| 34 | `VL_c1` | Speed loop enhancement coefficient | RW | (0.0, 10000.0] | float |

| ID | Variable | Description | Access | Range | Type |
|----|----------|-------------|--------|-------|------|
| 35 | `can_br` | CAN baud rate code | RW | [0, 4] | uint32 |
| 36 | `sub_ver` | Sub-version number | RO | / | uint32 |

| ID | Variable | Description | Access | Range | Type |
|----|----------|-------------|--------|-------|------|
| 50 | `u_off` | U-phase offset | RO | - | float |
| 51 | `v_off` | V-phase offset | RO | - | float |
| 52 | `k1` | Compensation factor 1 | RO | - | float |
| 53 | `k2` | Compensation factor 2 | RO | - | float |
| 54 | `m_off` | Angle offset | RO | - | float |
| 55 | `dir` | Direction | RO | - | float |

| ID | Variable | Description | Access | Range | Type |
|----|----------|-------------|--------|-------|------|
| 80 | `p_m` | Motor position | RO | - | float |
| 81 | `xout` | Output shaft position | RO | - | float |

# Motor Configuration

This guide covers configuring DaMiao motor parameters.

## Motor IDs

Each motor has two IDs:

### Motor ID (Command/Receive ID)

The ID used to send commands to the motor. This is typically set via hardware or firmware.

### Feedback ID (MST_ID)

The ID used to identify feedback messages from the motor. This can be configured via registers.

## Setting Motor ID

Motor IDs are typically set via:

1. Hardware jumpers/switches
2. Firmware configuration
3. Register writes (if supported)

Refer to your motor's firmware documentation for specific instructions.

## Setting Feedback ID

The feedback ID can be set via register writes:

```python
from damiao_motor import DaMiaoController

controller = DaMiaoController(channel="can0")
motor = controller.add_motor(motor_id=0x01, feedback_id=0x00, motor_type="4340")

# Write feedback ID register (check register table for correct ID)
motor.write_register(feedback_id_register, new_feedback_id)
```

## CAN Baud Rate

Configure the CAN baud rate to match your motor firmware:

```python
from damiao_motor import CAN_BAUD_RATE_CODES

# Available baud rates
print(CAN_BAUD_RATE_CODES)
```

The CAN interface bitrate should match the motor's configured baud rate.

## P/V/T and kp/kd Limits (MIT Mode)

P/V/T min/max are fixed per motor type (PMAX, VMAX, TMAX). The driver uses the selected `motor_type` preset for encoding commands and decoding feedback. **kp_min/kp_max and kd_min/kd_max are fixed** (kp: 0/500, kd: 0/5) for all motors; import `KP_MIN`, `KP_MAX`, `KD_MIN`, `KD_MAX` from `damiao_motor` if needed.

### Motor type and presets

Use the `motor_type` parameter when creating a motor. It selects the P/V/T preset (PMAX, VMAX, TMAX) for the motor model:

- **`motor_type`**: Required string. Use `"4340"` as a common default. Use `MOTOR_TYPE_PRESETS` to inspect presets.

| Motor type | PMAX | VMAX | TMAX |
|------------|------|------|------|
| 4310 | 12.5 | 30 | 10 |
| 4310P | 12.5 | 50 | 10 |
| 4340 | 12.5 | 10 | 28 |
| 4340P | 12.5 | 10 | 28 |
| 6006 | 12.5 | 45 | 20 |
| 8006 | 12.5 | 45 | 40 |
| 8009 | 12.5 | 45 | 54 |
| 10010L | 12.5 | 25 | 200 |
| 10010 | 12.5 | 20 | 200 |
| H3510 | 12.5 | 280 | 1 |
| G6215 | 12.5 | 45 | 10 |
| H6220 | 12.5 | 45 | 10 |
| JH11 | 12.5 | 10 | 12 |
| 6248P | 12.566 | 20 | 120 |
| 3507 | 12.566 | 50 | 5 |

```python
from damiao_motor import DaMiaoController, MOTOR_TYPE_PRESETS

controller = DaMiaoController(channel="can0")
# 4340 (common default)
motor = controller.add_motor(motor_id=0x01, feedback_id=0x00, motor_type="4340")

# Other motor types
motor = controller.add_motor(motor_id=0x02, feedback_id=0x01, motor_type="4310")
motor = controller.add_motor(motor_id=0x03, feedback_id=0x02, motor_type="3507")
```

### Overriding Limits

Pass `p_min`, `p_max`, `v_min`, `v_max`, `t_min`, `t_max` to override the preset, or use `set_limits()`, `set_p_limits()`, `set_v_limits()`, `set_t_limits()`. (kp and kd ranges are fixed for all motors: kp 0–500, kd 0–5.)

## Register Configuration

### Reading Registers

```python
value = motor.get_register(register_id)
```

### Writing Registers

```python
success = motor.write_register(register_id, value)
```

### Using Web GUI

The web GUI provides an easy way to view and edit all registers. Use the `damiao-gui` command-line tool to launch the web interface.

## Common Configurations

### Single Motor

```python
controller = DaMiaoController(channel="can0")
motor = controller.add_motor(motor_id=0x01, feedback_id=0x00, motor_type="4340")
```

### Multiple Motors (Same Feedback ID)

```python
controller = DaMiaoController(channel="can0")
for motor_id in [0x01, 0x02, 0x03]:
    controller.add_motor(motor_id=motor_id, feedback_id=0x00, motor_type="4340")
```

### Multiple Motors (Different Feedback IDs)

```python
controller = DaMiaoController(channel="can0")
controller.add_motor(motor_id=0x01, feedback_id=0x00, motor_type="4340")
controller.add_motor(motor_id=0x02, feedback_id=0x01, motor_type="4340")
controller.add_motor(motor_id=0x03, feedback_id=0x02, motor_type="4340")
```

## Control Gains

Typical control gains:

- **Stiffness (kp)**: 10-50 (position gain)
- **Damping (kd)**: 0.1-2.0 (velocity gain)

Adjust based on your application requirements.

## Safety Configuration

!!! warning "Safety First"
    - Always verify motor configuration before enabling
    - Test with low gains first
    - Ensure proper limits are set
    - Use emergency stop mechanisms

## Next Steps

- [CAN Setup](can-setup.md) - Configure CAN interface
- [API Reference](../api/controller.md) - Complete API documentation


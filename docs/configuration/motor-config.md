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
motor = controller.add_motor(motor_id=0x01, feedback_id=0x00)

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

## Register Configuration

### Reading Registers

```python
value = motor.read_register(register_id)
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
motor = controller.add_motor(motor_id=0x01, feedback_id=0x00)
```

### Multiple Motors (Same Feedback ID)

```python
controller = DaMiaoController(channel="can0")
for motor_id in [0x01, 0x02, 0x03]:
    controller.add_motor(motor_id=motor_id, feedback_id=0x00)
```

### Multiple Motors (Different Feedback IDs)

```python
controller = DaMiaoController(channel="can0")
controller.add_motor(motor_id=0x01, feedback_id=0x00)
controller.add_motor(motor_id=0x02, feedback_id=0x01)
controller.add_motor(motor_id=0x03, feedback_id=0x02)
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


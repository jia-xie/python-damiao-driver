# CLI Tool Reference

The `damiao` command-line tool provides a unified interface for scanning, configuring, and controlling DaMiao motors.

## Getting Help

To see all available commands:

```bash
damiao --help
```

To get help for a specific command:

```bash
damiao <command> --help
```

## Commands

### scan

Scan for connected motors on the CAN bus.

```bash
damiao scan [OPTIONS]
```

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--ids` | `ID [ID ...]` | Motor IDs to test (e.g., `--ids 1 2 3`). If not specified, tests IDs 0x01-0x10. |
| `--duration` | `FLOAT` | Duration to listen for responses in seconds (default: 0.5) |
| `--debug` | flag | Print all raw CAN messages for debugging |
| `--channel` | `STR` | CAN channel (default: can0) |
| `--bustype` | `STR` | CAN bus type (default: socketcan) |
| `--bitrate` | `INT` | CAN bitrate in bits per second (default: 1000000) |

**Examples:**
```bash
# Scan default ID range (0x01-0x10) - motor-type is optional
damiao scan

# Scan specific motor IDs
damiao scan --ids 1 2 3

# Scan with longer listen duration
damiao scan --duration 2.0

# Scan with specific motor type (optional, defaults to 4310)
damiao scan --motor-type 4340

# Scan with debug output
damiao scan --debug
```

### send-cmd

Send command to motor with specified control mode. Loops continuously until Ctrl+C. See [Motor Control Modes](../concept/motor-control-modes.md) for details on available control modes.

```bash
damiao send-cmd [OPTIONS]
```

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--id` | `INT` | Motor ID (required) |
| `--mode` | `{MIT,position_velocity,velocity,force_position_hybrid}` | Control mode (default: MIT) |
| `--position` | `FLOAT` | Desired position (radians). Required for MIT, position_velocity, force_position_hybrid modes. |
| `--velocity` | `FLOAT` | Desired velocity (rad/s). Required for MIT, position_velocity, velocity modes. |
| `--stiffness` | `FLOAT` | Stiffness (kp) for MIT mode (default: 0.0) |
| `--damping` | `FLOAT` | Damping (kd) for MIT mode (default: 0.0) |
| `--feedforward-torque` | `FLOAT` | Feedforward torque for MIT mode (default: 0.0) |
| `--velocity-limit` | `FLOAT` | Velocity limit (rad/s, 0-100) for force_position_hybrid mode |
| `--current-limit` | `FLOAT` | Torque current limit normalized (0.0-1.0) for force_position_hybrid mode |
| `--frequency` | `FLOAT` | Command frequency in Hz (default: 100.0) |
| `--channel` | `STR` | CAN channel (default: can0) |
| `--bustype` | `STR` | CAN bus type (default: socketcan) |
| `--bitrate` | `INT` | CAN bitrate in bits per second (default: 1000000) |

**Examples:**
```bash
# MIT mode (default)
damiao send-cmd --id 1 --mode MIT --position 1.5 --velocity 0.0 --stiffness 3.0 --damping 0.5

# Position-Velocity mode
damiao send-cmd --id 1 --mode position_velocity --position 1.5 --velocity 2.0

# Velocity mode
damiao send-cmd --id 1 --mode velocity --velocity 3.0

# Force-Position Hybrid mode
damiao send-cmd --id 1 --mode force_position_hybrid --position 1.5 --velocity-limit 50.0 --current-limit 0.8

# With custom frequency
damiao send-cmd --id 1 --mode MIT --position 1.5 --frequency 50.0
```

### set-zero-command

Send zero command to a motor (pos=0, vel=0, torq=0, kp=0, kd=0). Loops continuously until Ctrl+C.

```bash
damiao set-zero-command [OPTIONS]
```

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--id` | `INT` | Motor ID to send zero command to (required) |
| `--frequency` | `FLOAT` | Command frequency in Hz (default: 100.0) |
| `--channel` | `STR` | CAN channel (default: can0) |
| `--bustype` | `STR` | CAN bus type (default: socketcan) |
| `--bitrate` | `INT` | CAN bitrate in bits per second (default: 1000000) |

**Examples:**
```bash
# Send zero command continuously
damiao set-zero-command --id 1

# With custom frequency
damiao set-zero-command --id 1 --frequency 50.0
```

### set-zero-position

Set the current output shaft position to zero.

```bash
damiao set-zero-position [OPTIONS]
```

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--id` | `INT` | Motor ID (required) |
| `--channel` | `STR` | CAN channel (default: can0) |
| `--bustype` | `STR` | CAN bus type (default: socketcan) |
| `--bitrate` | `INT` | CAN bitrate in bits per second (default: 1000000) |

**Examples:**
```bash
# Set current position to zero
damiao set-zero-position --id 1
```

### set-can-timeout

Set CAN timeout alarm time (register 9).

```bash
damiao set-can-timeout [OPTIONS]
```

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--id` | `INT` | Motor ID (required) |
| `--timeout` | `INT` | Timeout in milliseconds (ms) (required) |
| `--channel` | `STR` | CAN channel (default: can0) |
| `--bustype` | `STR` | CAN bus type (default: socketcan) |
| `--bitrate` | `INT` | CAN bitrate in bits per second (default: 1000000) |

**Examples:**
```bash
# Set CAN timeout to 1000 ms
damiao set-can-timeout --id 1 --timeout 1000
```

### set-motor-id

Change the motor's receive ID (ESC_ID, register 8). This is the ID used to send commands to the motor.

```bash
damiao set-motor-id [OPTIONS]
```

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--current` | `INT` | Current motor ID (to connect to the motor) (required) |
| `--target` | `INT` | Target motor ID (new receive ID) (required) |
| `--channel` | `STR` | CAN channel (default: can0) |
| `--bustype` | `STR` | CAN bus type (default: socketcan) |
| `--bitrate` | `INT` | CAN bitrate in bits per second (default: 1000000) |

**Examples:**
```bash
# Change motor ID from 1 to 2
damiao set-motor-id --current 1 --target 2
```

!!! note "Note"
    After changing the motor ID, you will need to use the new ID to communicate with the motor.

### set-feedback-id

Change the motor's feedback ID (MST_ID, register 7). This is the ID used to identify feedback messages from the motor.

```bash
damiao set-feedback-id [OPTIONS]
```

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--current` | `INT` | Current motor ID (to connect to the motor) (required) |
| `--target` | `INT` | Target feedback ID (new MST_ID) (required) |
| `--channel` | `STR` | CAN channel (default: can0) |
| `--bustype` | `STR` | CAN bus type (default: socketcan) |
| `--bitrate` | `INT` | CAN bitrate in bits per second (default: 1000000) |

**Examples:**
```bash
# Change feedback ID to 3 (using motor ID 1 to connect)
damiao set-feedback-id --current 1 --target 3
```

!!! note "Note"
    The motor will now respond with feedback using the new feedback ID.

### gui

Launch the web-based GUI for viewing and controlling DaMiao motors.

```bash
damiao gui [OPTIONS]
```

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--host` | `STR` | Host to bind to (default: 127.0.0.1) |
| `--port` | `INT` | Port to bind to (default: 5000) |
| `--debug` | flag | Enable debug mode |
| `--production` | flag | Use production WSGI server (requires waitress) |

**Examples:**
```bash
# Start GUI on default host and port (http://127.0.0.1:5000)
damiao gui

# Start GUI on custom port
damiao gui --port 8080

# Start GUI on all interfaces
damiao gui --host 0.0.0.0

# Start GUI with production server
damiao gui --production
```

!!! note "Backward Compatibility"
    The `damiao-gui` command is still available as an alias for backward compatibility, but `damiao gui` is the recommended way to launch the GUI.

## Global Options

All commands support the following global options:

| Option | Type | Description |
|--------|------|-------------|
| `--channel` | `STR` | CAN channel (default: can0) |
| `--bustype` | `STR` | CAN bus type (default: socketcan) |
| `--bitrate` | `INT` | CAN bitrate in bits per second (default: 1000000). Only used when bringing up interface. |

These options can be specified either before or after the subcommand:

```bash
damiao --channel can1 scan
damiao scan --channel can1
```

## Real-time Feedback

All looping send commands (`send-cmd`, `set-zero-command`) continuously print motor state information:

```
State: 1 (ENABLED) | Pos:   1.234 rad | Vel:   0.567 rad/s | Torq:   0.123 Nm | T_mos: 45.0°C | T_rotor: 50.0°C
```

The state information includes:
- **State**: Status code and human-readable status name
- **Pos**: Current position (radians)
- **Vel**: Current velocity (rad/s)
- **Torq**: Current torque (Nm)
- **T_mos**: MOSFET temperature (°C)
- **T_rotor**: Rotor temperature (°C)

## Safety Notes

!!! warning "Safety First"
    - Always ensure motors are securely mounted before sending commands
    - Start with zero commands or low values to verify motor response
    - Monitor motor temperatures during operation
    - Use Ctrl+C to stop looping commands immediately
    - Test in a safe environment before production use


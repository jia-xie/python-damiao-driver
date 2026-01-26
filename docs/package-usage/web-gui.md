---
tags:
  - usage
  - gui
  - web
---

# Web GUI

The `damiao gui` command provides a web-based interface to connect to the CAN bus, scan for DaMiao motors, run commands, view and edit registers, and plot position, velocity, and torque in real time.

![DaMiao Motor Control – full interface](gui-screenshot.png)

---

## Installation

Install the package; the `damiao` command will be available in your PATH:

```bash
pip install damiao-motor
```

## Starting the GUI

```bash
damiao gui
```

Open **http://127.0.0.1:5000** in your browser.

!!! note "Backward Compatibility"
    Use `damiao gui` to launch the GUI.

### Command options

| Option | Description |
|--------|-------------|
| `--host` | Host (default: 127.0.0.1) |
| `--port` | Port (default: 5000) |
| `--debug` | Enable debug mode |
| `--production` | Use production server (requires `pip install waitress`) |

Examples:

```bash
damiao gui --port 8080
damiao gui --host 0.0.0.0
damiao gui --production
```

---

## Interface layout

The page is split into:

- **Top bar**: Connection (CAN channel, Connect, Disconnect).
- **Left column**: Motor Selection, Motor Control (Control Parameters + Motor Feedback), Register Parameters.
- **Right column**: Chart Visualizations (Position, Velocity, Torque).

---

## Connection

- **CAN Channel**: Choose an interface (e.g. can0, vcan0). A refresh button reloads the list.
- **Connect**: Connects to the selected channel.
- **Disconnect**: Disconnects and clears detected motors.

A status log shows connection and scan progress (e.g. *Connecting…*, *Connected to CAN bus: can0*, *Scanning for motors…*, *Found N motor(s)*, *Registers loaded*).

![Connection bar – CAN channel, Connect, Disconnect, and status log](screenshots/connection.png)

---

## Motor Selection

- **Scan Motors**: Scans for motors and lists those that respond.
- **Motor dropdown**: *Select a motor…* when none is chosen; otherwise *Motor ID: 0xXX | Arb ID: 0xYY* for each detected motor. Selecting a motor updates the Control panel, Register Parameters, and charts.

![Motor Selection – Scan Motors and motor dropdown (Motor ID | Arb ID)](screenshots/motor-selection.png)

---

## Motor Control

When a motor is selected, the left column shows **Control Parameters** and **Motor Feedback**.

### Control Parameters

- **Motor type**: Choose the motor model (e.g. 4310, 4340, 6006, 8006, 8009, 10010/L, H3510, G6215, H6220, JH11, 6248P, 3507).
- **Control Mode**: MIT, POS_VEL, VEL, FORCE_POS. Row visibility depends on mode: Position, Velocity, Stiffness, Damping, Torque for MIT; Vel Limit and Current Limit for FORCE_POS.
- **Enable / Disable**: Enable or disable the motor.
- **Send Command**: Applies the current control parameters. **Single**: once. **Continuous**: at the set Command Frequency (1–1000 Hz).
- **Stop Command**: Stops Continuous mode and disables the motor.
- **Set Zero**: Saves the current position as zero.
- **Clear Error**: Clears the motor error.

![Motor type dropdown – supported motor models (4310, 4340, 6006, …)](screenshots/motor-type-selection.png)

### Motor Feedback

- **Status** (e.g. ENABLED, DISABLED) and live **Position**, **Velocity**, **Torque**, **MOS Temp**, **Rotor Temp** for the selected motor.

![Motor Control – Control Parameters (mode, position, velocity, Kp/Kd, torque, Enable/Disable, Send Command, Single/Continuous, Set Zero, Clear Error) and Motor Feedback](screenshots/motor-control.png)

---

## Register Parameters

- **Table**: **Description**, **Value**, **Type**, **Action**. **Read-only (RO)** registers have no Edit. **Writable (RW)** registers: click **Edit**, change the value, then **Save** or **Cancel**.
- **Special UIs**: Feedback ID and Motor ID use hex input; Control mode and CAN baud rate use dropdowns. Changing Feedback ID or Motor ID triggers a rescan so the motor list stays correct.

![Register Parameters – Description, Value, Type, Action; Edit with Save/Cancel for RW registers](screenshots/registers.png)

---

## Chart Visualizations

Three line charts: **Position (rad)**, **Velocity (rad/s)**, **Torque (Nm)**. Live data when a motor is selected (and when sending commands in Continuous mode).

For each chart:

- **Export Data**: Save the visible data as CSV.
- **Grid**: Toggle grid on/off.
- **Duration (s)**: Time window on the X-axis.
- **Y Min / Y Max**: Set Y-axis limits, or "Auto".
- **Reset Limits**: Restore Y-axis to the motor’s limits or auto.
- **Points**: Toggle data points.

Charts support zoom (scroll or pinch). Each chart shows live data over the set time window.

![Chart Visualizations – Position (rad), Velocity (rad/s), Torque (Nm) with Export Data, Grid, Duration, Y limits, Reset Limits, Points](screenshots/charts.png)

---

## Export Chart Data

Clicking **Export Data** on a chart opens a modal: enter a file name and **Save** to download a CSV of the chart’s visible data. The file is saved to your default download folder.

![Export Chart Data – file name, Save to CSV, Cancel](screenshots/export-data.png)

---

## Register editing (details)

- **RO**: Shown in gray; no Edit button.
- **RW**: Click **Edit**, change the value (or choose from the dropdown for Control mode and CAN baud rate), then **Save** or **Cancel**. Changing Feedback ID or Motor ID triggers a rescan so the motor list stays correct.

---

## Safety notes

!!! warning "Safety First"
    - Verify CAN interface and motor wiring before Connect.
    - Ensure the motor is securely mounted and the area is clear before Enable and Continuous commands.
    - Always verify register values before writing; some changes take effect immediately.
    - Changing Motor ID or Feedback ID changes how the motor is identified; the GUI rescans automatically.
    - Test register and command changes in a safe environment before production use.

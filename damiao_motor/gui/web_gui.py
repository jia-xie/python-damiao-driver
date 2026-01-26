#!/usr/bin/env python3
"""
Web-based GUI for viewing and changing DaMiao motor parameters.
"""
import json
from typing import Dict, Any, Optional

from flask import Flask, render_template, jsonify, request

from damiao_motor.core.controller import DaMiaoController
from damiao_motor.core.motor import REGISTER_TABLE, RegisterInfo, MOTOR_TYPE_PRESETS

import os

# Get the directory where this module is located
_template_dir = os.path.join(os.path.dirname(__file__), 'templates')
_static_dir = os.path.join(os.path.dirname(__file__), 'static')
app = Flask(__name__, template_folder=_template_dir, static_folder=_static_dir)

# Global controller instance (will be initialized when needed)
_controller: Optional[DaMiaoController] = None
_motors: Dict[int, Any] = {}


def init_controller(channel: str = "can0", bustype: str = "socketcan") -> None:
    """Initialize the CAN controller."""
    global _controller, _motors
    # Shutdown existing controller if any
    if _controller is not None:
        try:
            _controller.shutdown()
        except:
            pass
    _controller = DaMiaoController(channel=channel, bustype=bustype)
    _motors = {}




@app.route('/')
def index():
    """Serve the main GUI page."""
    return render_template('index.html')


@app.route('/api/register-table', methods=['GET'])
def get_register_table():
    """Get the register table information."""
    registers = []
    for rid, reg_info in REGISTER_TABLE.items():
        registers.append({
            'rid': reg_info.rid,
            'variable': reg_info.variable,
            'description': reg_info.description,
            'access': reg_info.access,
            'range_str': reg_info.range_str,
            'data_type': reg_info.data_type,
        })
    return jsonify({'success': True, 'registers': registers})


@app.route('/api/can-interfaces', methods=['GET'])
def list_can_interfaces():
    """List available CAN interfaces (e.g. can0, vcan0) on the system.
    On Linux with SocketCAN, reads /sys/class/net for names starting with 'can'.
    """
    interfaces = []
    try:
        net_dir = '/sys/class/net'
        if os.path.isdir(net_dir):
            for name in os.listdir(net_dir):
                if name.startswith('can'):
                    interfaces.append(name)
            interfaces.sort()
    except OSError:
        pass
    return jsonify({'success': True, 'interfaces': interfaces})


@app.route('/api/motor-types', methods=['GET'])
def get_motor_types():
    """Return list of supported motor type presets (e.g. 4340, 4310)."""
    return jsonify({'success': True, 'types': list(MOTOR_TYPE_PRESETS.keys())})


@app.route('/api/connect', methods=['POST'])
def connect():
    """Connect to CAN bus."""
    try:
        data = request.json
        channel = data.get('channel', 'can0')
        init_controller(channel=channel)
        return jsonify({'success': True})
    except Exception as e:
        error_msg = str(e)
        # Check if it's a "Network is down" error
        if "Error Code 100" in error_msg or "Network is down" in error_msg or "[Errno 100]" in error_msg:
            hint = (
                f"To fix this, bring up the CAN interface:\n"
                f"  sudo ip link set {channel} up type can bitrate 1000000\n\n"
                f"Or check the interface status:\n"
                f"  ip link show {channel}"
            )
            return jsonify({'success': False, 'error': error_msg, 'hint': hint}), 500
        return jsonify({'success': False, 'error': error_msg}), 500


@app.route('/api/disconnect', methods=['POST'])
def disconnect():
    """Disconnect from CAN bus."""
    global _controller, _motors
    try:
        if _controller:
            _controller.shutdown()  # Use shutdown() which properly stops polling
        _controller = None
        _motors = {}
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/scan', methods=['POST'])
def scan():
    """Scan for motors."""
    global _controller, _motors
    try:
        if _controller is None:
            return jsonify({'success': False, 'error': 'Not connected. Please connect first.'}), 400

        data = request.get_json() or {}
        motor_type = data.get('motor_type')
        if not motor_type:
            return jsonify({'success': False, 'error': 'motor_type is required'}), 400

        # Clear existing motors
        _motors = {}
        _controller.motors = {}
        _controller._motors_by_feedback = {}
        
        # Flush bus
        try:
            _controller.flush_bus()
        except Exception as e:
            error_msg = str(e)
            # Check if it's a "Network is down" error
            if "Error Code 100" in error_msg or "Network is down" in error_msg or "[Errno 100]" in error_msg:
                # Extract channel name if available
                channel = getattr(_controller.bus, 'channel', 'can0')
                hint = (
                    f"To fix this, bring up the CAN interface:\n"
                    f"  sudo ip link set {channel} up type can bitrate 1000000\n\n"
                    f"Or check the interface status:\n"
                    f"  ip link show {channel}"
                )
                return jsonify({'success': False, 'error': error_msg, 'hint': hint}), 500
            # Re-raise other errors
            raise
        
        # Send zero commands to potential motor IDs (0x01-0x10)
        motors_found = []
        for motor_id in range(0x01, 0x11):
            try:
                motor = _controller.add_motor(motor_id=motor_id, feedback_id=0x00, motor_type=motor_type)
                motor.send_cmd_mit(target_position=0.0, target_velocity=0.0, stiffness=0.0, damping=0.0, feedforward_torque=0.0)
            except ValueError:
                pass  # Motor already exists
            except Exception as e:
                # Log but continue
                print(f"Warning: Failed to send command to motor {motor_id}: {e}")
        
        # Listen for responses
        import time
        start_time = time.perf_counter()
        responded = set()
        
        while time.perf_counter() - start_time < 0.5:
            _controller.poll_feedback()
            for motor_id, motor in _controller.motors.items():
                if motor.state and motor.state.get("can_id") is not None:
                    if motor_id not in responded:
                        arb_id = motor.state.get("arbitration_id")
                        motors_found.append({
                            'id': motor_id,
                            'arb_id': arb_id if arb_id is not None else 0,
                            'motor_type': motor.motor_type,
                        })
                        responded.add(motor_id)
            time.sleep(0.01)
        
        _motors = {m['id']: _controller.motors[m['id']] for m in motors_found}
        
        return jsonify({'success': True, 'motors': motors_found})
    except Exception as e:
        import traceback
        error_msg = str(e)
        error_full = f"{error_msg}\n{traceback.format_exc()}"
        print(f"Scan error: {error_full}")
        
        # Check if it's a "Network is down" error and provide hint
        if "Error Code 100" in error_msg or "Network is down" in error_msg or "[Errno 100]" in error_msg:
            channel = getattr(_controller.bus, 'channel', 'can0') if _controller else 'can0'
            hint = (
                f"To fix this, bring up the CAN interface:\n"
                f"  sudo ip link set {channel} up type can bitrate 1000000\n\n"
                f"Or check the interface status:\n"
                f"  ip link show {channel}"
            )
            return jsonify({'success': False, 'error': error_msg, 'hint': hint}), 500
        
        return jsonify({'success': False, 'error': error_msg}), 500


@app.route('/api/motors/<int:motor_id>/registers', methods=['GET'])
def get_registers(motor_id: int):
    """Get all registers for a motor."""
    global _motors
    try:
        if motor_id not in _motors:
            return jsonify({'success': False, 'error': f'Motor {motor_id} not found'}), 404
        
        motor = _motors[motor_id]
        registers = motor.read_all_registers(timeout=0.05)
        
        # Filter out error strings
        clean_registers = {}
        for rid, value in registers.items():
            if not isinstance(value, str) or not value.startswith("ERROR"):
                clean_registers[rid] = value
        
        return jsonify({'success': True, 'registers': clean_registers, 'motor_type': motor.motor_type})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/motors/<int:motor_id>/registers/<int:rid>', methods=['PUT'])
def set_register(motor_id: int, rid: int):
    """Set a register value."""
    global _controller, _motors
    try:
        if motor_id not in _motors:
            return jsonify({'success': False, 'error': f'Motor {motor_id} not found'}), 404
        
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Content-Type must be application/json'}), 400
        
        data = request.get_json()
        if data is None:
            return jsonify({'success': False, 'error': 'Invalid JSON in request body'}), 400
        
        value = data.get('value')
        
        if value is None:
            return jsonify({'success': False, 'error': 'Value is required'}), 400
        
        motor = _motors[motor_id]
        
        # Note: Register 9 (TIMEOUT) uses units of 50 microseconds (1 unit = 50us)
        # To convert from milliseconds: register_value = timeout_ms × 20
        # For example: 1000 ms = 20,000 register units, 50 ms = 1,000 register units
        motor.write_register(rid, value)
        
        # If we changed register 7 (MST_ID/feedback_id) or 8 (ESC_ID/receive_id),
        # we need to update the motor's IDs and controller mappings
        updated_ids = {}
        if rid == 7:  # MST_ID - feedback ID
            new_feedback_id = int(value)
            old_feedback_id = motor.feedback_id
            motor.feedback_id = new_feedback_id
            
            # Update controller's feedback mapping
            if old_feedback_id in _controller._motors_by_feedback:
                del _controller._motors_by_feedback[old_feedback_id]
            _controller._motors_by_feedback[new_feedback_id] = motor
            
            updated_ids['feedback_id'] = new_feedback_id
            
        elif rid == 8:  # ESC_ID - receive/command ID
            new_motor_id = int(value)
            old_motor_id = motor.motor_id
            
            # Update motor's motor_id
            motor.motor_id = new_motor_id
            
            # Update controller's motor mapping
            if old_motor_id in _controller.motors:
                del _controller.motors[old_motor_id]
            _controller.motors[new_motor_id] = motor
            
            # Update _motors dict
            if old_motor_id in _motors:
                _motors[new_motor_id] = _motors.pop(old_motor_id)
            
            updated_ids['motor_id'] = new_motor_id
        
        # Store parameters to flash if it's a critical register
        if rid in [7, 8]:
            try:
                motor.store_parameters()
            except:
                pass  # Ignore errors, motor might not support it
        
        return jsonify({'success': True, 'updated_ids': updated_ids})
    except KeyError as e:
        return jsonify({'success': False, 'error': f'Register {rid} not found in register table'}), 400
    except ValueError as e:
        return jsonify({'success': False, 'error': f'Invalid value: {str(e)}'}), 400
    except TimeoutError as e:
        return jsonify({'success': False, 'error': f'Timeout writing register: {str(e)}'}), 500
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Set register error: {error_msg}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/motors/<int:motor_id>/enable', methods=['POST'])
def enable_motor(motor_id: int):
    """Enable a motor."""
    global _motors
    try:
        if motor_id not in _motors:
            return jsonify({'success': False, 'error': f'Motor {motor_id} not found'}), 404
        
        motor = _motors[motor_id]
        motor.enable()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/motors/<int:motor_id>/disable', methods=['POST'])
def disable_motor(motor_id: int):
    """Disable a motor. Sends a zero-command first to zero torque, then the disable message."""
    global _motors
    try:
        if motor_id not in _motors:
            return jsonify({'success': False, 'error': f'Motor {motor_id} not found'}), 404
        
        motor = _motors[motor_id]
        motor.set_zero_command()  # zero torque before disable
        motor.disable()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/motors/<int:motor_id>/state', methods=['GET'])
def get_motor_state(motor_id: int):
    """Get current motor state/feedback."""
    global _motors, _controller
    try:
        if motor_id not in _motors:
            return jsonify({'success': False, 'error': f'Motor {motor_id} not found'}), 404
        
        motor = _motors[motor_id]
        
        # Poll for latest feedback
        if _controller:
            _controller.poll_feedback()
        
        state = {**motor.get_states(), "motor_type": motor.motor_type}
        return jsonify({'success': True, 'state': state})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/motors/<int:motor_id>/command', methods=['POST'])
def send_motor_command(motor_id: int):
    """Send a command to the motor."""
    global _motors, _controller
    try:
        if motor_id not in _motors:
            return jsonify({'success': False, 'error': f'Motor {motor_id} not found'}), 404
        
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Content-Type must be application/json'}), 400
        
        data = request.get_json()
        if data is None:
            return jsonify({'success': False, 'error': 'Invalid JSON in request body'}), 400
        
        motor = _motors[motor_id]
        
        # Get command parameters
        control_mode = data.get('control_mode', 'MIT')
        target_position = data.get('target_position', 0.0)
        target_velocity = data.get('target_velocity', 0.0)
        stiffness = data.get('stiffness', 0.0)
        damping = data.get('damping', 0.0)
        feedforward_torque = data.get('feedforward_torque', 0.0)
        velocity_limit = data.get('velocity_limit', 0.0)
        current_limit = data.get('current_limit', 0.0)
        
        # Send command using appropriate method based on control mode
        if control_mode == "MIT":
            motor.send_cmd_mit(
                target_position=target_position,
                target_velocity=target_velocity,
                stiffness=stiffness,
                damping=damping,
                feedforward_torque=feedforward_torque,
            )
        elif control_mode == "POS_VEL":
            motor.send_cmd_pos_vel(
                target_position=target_position,
                target_velocity=target_velocity,
            )
        elif control_mode == "VEL":
            motor.send_cmd_vel(
                target_velocity=target_velocity,
            )
        elif control_mode == "FORCE_POS":
            motor.send_cmd_force_pos(
                target_position=target_position,
                velocity_limit=velocity_limit,
                current_limit=current_limit,
            )
        else:
            return jsonify({'success': False, 'error': f'Unknown control_mode: {control_mode}'}), 400
        
        # Poll and return state at same rate as control (avoids separate state fetch)
        if _controller:
            _controller.poll_feedback()
        state = motor.get_states()
        return jsonify({'success': True, 'state': state})
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Send command error: {error_msg}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/motors/<int:motor_id>/set-zero', methods=['POST'])
def set_zero_position(motor_id: int):
    """Set the current position to zero."""
    global _motors
    try:
        if motor_id not in _motors:
            return jsonify({'success': False, 'error': f'Motor {motor_id} not found'}), 404
        
        motor = _motors[motor_id]
        motor.set_zero_position()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/motors/<int:motor_id>/clear-error', methods=['POST'])
def clear_motor_error(motor_id: int):
    """Clear motor errors."""
    global _motors
    try:
        if motor_id not in _motors:
            return jsonify({'success': False, 'error': f'Motor {motor_id} not found'}), 404
        
        motor = _motors[motor_id]
        motor.clear_error()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/motors/<int:motor_id>/motor-type', methods=['PUT'])
def set_motor_type(motor_id: int):
    """Set motor type (preset for P/V/T limits)."""
    global _motors
    try:
        if motor_id not in _motors:
            return jsonify({'success': False, 'error': f'Motor {motor_id} not found'}), 404

        data = request.get_json() or {}
        motor_type = data.get('motor_type')
        if not motor_type:
            return jsonify({'success': False, 'error': 'motor_type is required'}), 400

        motor = _motors[motor_id]
        motor.set_motor_type(motor_type)
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def run_server(host='127.0.0.1', port=5000, debug=False, production=False):
    """
    Run the web GUI server.
    
    Args:
        host: Host to bind to (default: 127.0.0.1)
        port: Port to bind to (default: 5000)
        debug: Enable debug mode (default: False)
        production: Use production WSGI server (default: False)
    """
    import warnings
    
    print(f"Starting DaMiao Motor Parameter Editor...")
    print(f"Open http://{host}:{port} in your browser")
    
    if production:
        try:
            from waitress import serve
            print("Using Waitress production server")
            serve(app, host=host, port=port)
        except ImportError:
            print("Warning: waitress not installed. Install with: pip install waitress")
            print("Falling back to development server...")
            # Suppress the warning for development server
            import logging
            log = logging.getLogger('werkzeug')
            log.setLevel(logging.ERROR)
            app.run(host=host, port=port, debug=debug)
    else:
        # Suppress the development server warning for local use
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        warnings.filterwarnings('ignore', message='.*development server.*')
        app.run(host=host, port=port, debug=debug)


def main():
    """Run the web GUI server (CLI entry point)."""
    import argparse
    parser = argparse.ArgumentParser(description="Web-based GUI for DaMiao motor parameters")
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to (default: 5000)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--production', action='store_true', help='Use production WSGI server (requires waitress)')
    args = parser.parse_args()
    
    run_server(host=args.host, port=args.port, debug=args.debug, production=args.production)


if __name__ == '__main__':
    main()


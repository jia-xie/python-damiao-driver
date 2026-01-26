import threading
import time
from typing import Any, Dict, Iterable, Optional

import can

from .motor import DaMiaoMotor


class DaMiaoController:
    """
    Simple multi-motor controller.

    - Owns a single CAN bus.
    - Manages multiple DaMiaoMotor instances on that bus.
    - Automatically polls feedback in background when motors are present.
    - Provides helper methods to:
        * enable/disable all motors
        * send commands to one or all motors
        * poll feedback non-blockingly
    """

    def __init__(self, channel: str = "can0", bustype: str = "socketcan") -> None:
        self.bus: can.Bus = can.interface.Bus(channel=channel, bustype=bustype)
        # Keyed by command CAN ID (motor_id)
        self.motors: Dict[int, DaMiaoMotor] = {}
        # Keyed by logical motor ID (embedded in feedback frame)
        self._motors_by_feedback: Dict[int, DaMiaoMotor] = {}
        # Background polling thread
        self._polling_thread: Optional[threading.Thread] = None
        self._polling_active = False
        self._polling_lock = threading.Lock()

    # -----------------------
    # Motor management
    # -----------------------
    def add_motor(self, motor_id: int, feedback_id: int, motor_type: str, **kwargs: Any) -> DaMiaoMotor:
        if motor_id in self.motors:
            raise ValueError(f"Motor with ID {motor_id} already exists")

        motor = DaMiaoMotor(
            motor_id=motor_id,
            feedback_id=feedback_id,
            bus=self.bus,
            motor_type=motor_type,
            **kwargs,
        )
        self.motors[motor_id] = motor
        # Bind by logical motor ID; feedback frames embed this ID in the first byte.
        self._motors_by_feedback[motor_id] = motor
        motor._controller = self

        # Start background polling if not already running
        self._start_polling()
        
        return motor

    def get_motor(self, motor_id: int) -> DaMiaoMotor:
        return self.motors[motor_id]

    def all_motors(self) -> Iterable[DaMiaoMotor]:
        return self.motors.values()

    # -----------------------
    # Enable / disable
    # -----------------------
    def enable_all(self) -> None:
        for m in self.all_motors():
            m.enable()

    def disable_all(self) -> None:
        for m in self.all_motors():
            m.disable()

    # -----------------------
    # Command helpers
    # -----------------------
    def send_cmd(
        self,
        motor_id: int,
        target_position: float = 0.0,
        target_velocity: float = 0.0,
        stiffness: float = 0.0,
        damping: float = 0.0,
        feedforward_torque: float = 0.0,
    ) -> None:
        """Send MIT mode command to a specific motor (convenience method)."""
        self.get_motor(motor_id).send_cmd_mit(
            target_position=target_position,
            target_velocity=target_velocity,
            stiffness=stiffness,
            damping=damping,
            feedforward_torque=feedforward_torque,
        )

    def send_cmd_all(
        self,
        target_position: float = 0.0,
        target_velocity: float = 0.0,
        stiffness: float = 0.0,
        damping: float = 0.0,
        feedforward_torque: float = 0.0,
    ) -> None:
        """Send MIT mode command to all motors (convenience method)."""
        for m in self.all_motors():
            m.send_cmd_mit(
                target_position=target_position,
                target_velocity=target_velocity,
                stiffness=stiffness,
                damping=damping,
                feedforward_torque=feedforward_torque,
            )

    # -----------------------
    # Bus management
    # -----------------------
    def flush_bus(self) -> int:
        """
        Flush all pending messages from the CAN bus buffer.
        
        Returns:
            Number of messages flushed.
        
        Raises:
            can.CanOperationError: If CAN interface is down (Error Code 100) with helpful hint
            OSError: If other network/system errors occur
        """
        count = 0
        try:
            while True:
                msg = self.bus.recv(timeout=0)
                if msg is None:
                    break
                count += 1
        except can.CanOperationError as e:
            error_str = str(e)
            errno = getattr(e, 'errno', None)
            
            # Error Code 100: Network is down - CAN interface not up
            if errno == 100 or "Error Code 100" in error_str or "Network is down" in error_str or "[Errno 100]" in error_str:
                channel = getattr(self.bus, 'channel', 'can0')
                raise can.CanOperationError(
                    f"CAN interface '{channel}' is down (Error Code 100)"
                ) from e
            # Re-raise other CanOperationError
            raise
        except OSError as e:
            errno = getattr(e, 'errno', None)
            if errno == 100 or "Network is down" in str(e) or "[Errno 100]" in str(e):
                channel = getattr(self.bus, 'channel', 'can0')
                raise OSError(
                    f"CAN interface '{channel}' is down (Error Code 100)"
                ) from e
            raise
        return count

    # -----------------------
    # Feedback polling
    # -----------------------
    def poll_feedback(self) -> None:
        """
        Non-blocking read of all pending CAN frames on this bus, and dispatch
        feedback frames to the corresponding motors.
        """
        try:
            while True:
                msg = self.bus.recv(timeout=0)
                if msg is None:
                    break

                if len(msg.data) != 8:
                    continue

                # Feedback messages include the logical motor ID in the low 4 bits
                # of the first data byte. Use that to route feedback to the right motor.
                logical_id = msg.data[0] & 0x0F
                motor = self._motors_by_feedback.get(logical_id)
                if motor is None:
                    continue

                motor.process_feedback_frame(bytes(msg.data), arbitration_id=msg.arbitration_id)
        except (ValueError, OSError, AttributeError):
            # Bus is closed or invalid, stop polling
            with self._polling_lock:
                self._polling_active = False

    # -----------------------
    # Background polling
    # -----------------------
    def _start_polling(self) -> None:
        """Start background polling thread if not already running."""
        with self._polling_lock:
            if self._polling_active:
                return
            
            if len(self.motors) == 0:
                return
            
            self._polling_active = True
            self._polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
            self._polling_thread.start()

    def _stop_polling(self) -> None:
        """Stop background polling thread."""
        with self._polling_lock:
            self._polling_active = False
            if self._polling_thread is not None:
                self._polling_thread.join(timeout=0.1)
                self._polling_thread = None

    def _polling_loop(self) -> None:
        """
        Background thread that continuously polls feedback.
        
        """
        while self._polling_active:
            if len(self.motors) == 0:
                # No motors, stop polling
                with self._polling_lock:
                    self._polling_active = False
                break
            
            try:
                self.poll_feedback()
            except Exception:
                # Bus error or other exception, stop polling
                with self._polling_lock:
                    self._polling_active = False
                break
            
            time.sleep(0.001)  # Small delay to prevent CPU spinning

    def _handle_register_reply(self, data: bytes) -> None:
        """
        Handle a register reply frame.
        Delegates to the motor instance to handle the reply.
        
        Args:
            data: 8-byte CAN frame data
        """
        if len(data) < 8:
            return
        
        # Register reply format: D[0]=CANID_L, D[1]=CANID_H, D[2]=0x33, D[3]=RID, D[4-7]=data
        canid_l = data[0]
        canid_h = data[1]
        rid = data[3]
        register_data = data[4:8]  # 4-byte register value
        
        # Reconstruct motor_id from CANID_L and CANID_H
        motor_id = canid_l | (canid_h << 8)
        
        # Get the motor instance
        motor = self.motors.get(motor_id)
        if motor is None:
            return
        
        # Let the motor handle the register reply
        motor.handle_register_reply(rid, register_data)
    
    def shutdown(self) -> None:
        """Shutdown the controller and stop background polling."""
        self._stop_polling()
        self.disable_all()
        self.bus.shutdown()



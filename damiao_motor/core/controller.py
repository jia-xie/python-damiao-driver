import sys
import threading
import time
from typing import Any, Dict, Iterable, Optional

import can

from .motor import DaMiaoMotor


def _patch_gs_usb_for_macos() -> None:
    """Patch gs_usb for macOS compatibility.

    Applies two monkey-patches to work around macOS-specific libusb / gs_usb
    behaviour that would otherwise prevent reconnecting without replugging:

    1. ``GsUsb.start`` — the upstream ``start()`` calls ``device.reset()`` before
       sending the GS_CAN_MODE_START control transfer.  On macOS a USB bus reset
       causes the device to re-enumerate with a new address, which invalidates the
       existing ``Device`` object and makes the subsequent ``ctrl_transfer`` fail
       (~10 % of reconnect attempts).  We suppress the ``reset()`` call; the
       GS_CAN_MODE_START ctrl_transfer is sufficient to (re-)activate the CAN
       controller without a USB-level reset.

    2. ``GsUsb.stop`` — ``stop()`` sends GS_CAN_MODE_RESET but never releases the
       USB interface, so within the same process the interface stays soft-claimed
       by libusb and every reconnect attempt fails.  We add a
       ``usb.util.release_interface()`` call after the mode reset.
    """
    try:
        import usb.util  # type: ignore[import-untyped]
        from gs_usb.gs_usb import GsUsb as _GsUsb  # type: ignore[import-untyped]
    except ImportError:
        return  # pyusb / gs_usb not installed, nothing to patch

    # --- Patch 1: GsUsb.start — skip device.reset() ---
    _original_gs_usb_start = _GsUsb.start

    def _patched_gs_usb_start(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        # Temporarily replace reset with a no-op so that device.reset() inside
        # start() is skipped.  On macOS the USB bus reset triggers re-enumeration
        # which invalidates the Device object; the GS_CAN_MODE_START ctrl_transfer
        # is sufficient to (re-)activate the CAN controller without a USB reset.
        _orig_reset = self.gs_usb.reset
        self.gs_usb.reset = lambda: None
        try:
            _original_gs_usb_start(self, *args, **kwargs)
        finally:
            self.gs_usb.reset = _orig_reset

    _GsUsb.start = _patched_gs_usb_start

    # --- Patch 2: GsUsb.stop — release USB interface ---
    _original_gs_usb_stop = _GsUsb.stop

    def _patched_gs_usb_stop(self):  # type: ignore[no-untyped-def]
        _original_gs_usb_stop(self)
        try:
            usb.util.release_interface(self.gs_usb, 0)
        except usb.core.USBError:
            pass  # ignore if already released or not claimed

    _GsUsb.stop = _patched_gs_usb_stop


if sys.platform == "darwin":
    _patch_gs_usb_for_macos()


def _resolve_gs_usb_channel(channel: str) -> int:
    """Resolve a gs_usb channel string to a device index.

    Accepts either:
    - A numeric string (``"0"``, ``"1"``, …) — used directly as the device index.
    - A USB serial number string — scanned against connected gs_usb devices.

    Args:
        channel: Numeric index string or USB serial number.

    Returns:
        Integer device index suitable for ``can.Bus(channel=<index>, interface="gs_usb")``.

    Raises:
        RuntimeError: If no gs_usb device with the given serial number is found.
        ImportError: If ``gs_usb`` is not installed.
    """
    if channel.isdigit():
        return int(channel)

    from gs_usb.gs_usb import GsUsb  # type: ignore[import-untyped]

    devs = GsUsb.scan()
    for i, dev in enumerate(devs):
        if dev.serial_number == channel:
            return i
    raise RuntimeError(
        f"No gs_usb device with serial number {channel!r} found. "
        f"Connected devices: {[d.serial_number for d in devs]}"
    )


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

    def __init__(
        self,
        channel: str = "can0",
        bustype: str = "socketcan",
        bitrate: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """
        Args:
            channel: For ``socketcan``: the network interface name (e.g. ``"can0"``).
                     For ``gs_usb``: either a numeric index string or a USB serial
                     number string.

                     - ``"0"``, ``"1"``, … — device index; ``"0"`` is the first
                       detected device, ``"1"`` the second, and so on.
                     - ``"DEADBEEF"`` (or any non-numeric string) — resolved by
                       scanning connected devices and matching the serial number.

                     To list connected gs_usb devices with their indices and serial
                     numbers, run::

                         uv run python -c "
                         from gs_usb.gs_usb import GsUsb
                         for i, d in enumerate(GsUsb.scan()):
                             print(i, d.serial_number, d.gs_usb.port_numbers)
                         "

            bustype: python-can interface name (``"socketcan"`` or ``"gs_usb"``).
            bitrate: CAN bitrate in bits/s.  Required for ``gs_usb``; ignored for
                     ``socketcan`` (bitrate is set at the OS level via ``ip link``).
            **kwargs: Extra arguments forwarded to ``can.interface.Bus``.
        """
        if bustype == "gs_usb":
            channel = _resolve_gs_usb_channel(channel)
        bus_kwargs: Dict[str, Any] = {
            "channel": channel,
            "interface": bustype,
            **kwargs,
        }
        if bitrate is not None:
            bus_kwargs["bitrate"] = bitrate
        self.bus: can.Bus = can.interface.Bus(**bus_kwargs)
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
    def add_motor(
        self, motor_id: int, feedback_id: int, motor_type: str, **kwargs: Any
    ) -> DaMiaoMotor:
        """
        Create and register a motor on this controller.

        Args:
            motor_id: Command CAN ID (ESC_ID) used to send commands to the motor.
            feedback_id: Feedback CAN ID (MST_ID) configured on the motor.
            motor_type: Motor type preset name (for example ``"4310"``, ``"4340"``).
            **kwargs: Extra arguments forwarded to ``DaMiaoMotor`` constructor.

        Returns:
            The created ``DaMiaoMotor`` instance.

        Raises:
            ValueError: If a motor with the same ``motor_id`` is already registered.
        """
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
        """
        Get a registered motor by command ID.

        Args:
            motor_id: Command CAN ID (ESC_ID) used when the motor was added.

        Returns:
            The matching ``DaMiaoMotor`` instance.
        """
        return self.motors[motor_id]

    def all_motors(self) -> Iterable[DaMiaoMotor]:
        """
        Iterate over all registered motors.

        Returns:
            Iterable of ``DaMiaoMotor`` instances.
        """
        return self.motors.values()

    # -----------------------
    # Enable / disable
    # -----------------------
    def enable_all(self) -> None:
        """Enable all registered motors."""
        for m in self.all_motors():
            m.enable()

    def disable_all(self) -> None:
        """Disable all registered motors."""
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
            errno = getattr(e, "errno", None)

            # Error Code 100: Network is down - CAN interface not up
            if (
                errno == 100
                or "Error Code 100" in error_str
                or "Network is down" in error_str
                or "[Errno 100]" in error_str
            ):
                channel = getattr(self.bus, "channel", "can0")
                raise can.CanOperationError(
                    f"CAN interface '{channel}' is down (Error Code 100)"
                ) from e
            # Re-raise other CanOperationError
            raise
        except OSError as e:
            errno = getattr(e, "errno", None)
            if errno == 100 or "Network is down" in str(e) or "[Errno 100]" in str(e):
                channel = getattr(self.bus, "channel", "can0")
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
        Drain pending CAN frames (non-blocking) and dispatch feedback to motors.

        Behavior:
        - Uses ``self.bus.recv(timeout=0)`` in a loop to read all currently queued
          frames without blocking.
        - Stops the loop when ``recv`` returns ``None`` (queue is empty).
        - Ignores frames that are not 8 bytes.
        - Routes frames by logical motor ID encoded in the low 4 bits of ``D[0]``.
        - For matched motors, forwards frames to
          ``DaMiaoMotor.process_feedback_frame(...)``.

        Notes:
        - This method performs one drain pass. It can be called manually, and is
          also used repeatedly by the background polling thread.
        - If bus/controller state becomes invalid (for example bus closed),
          polling is marked inactive to let background loop exit cleanly.
        """
        try:
            while True:
                msg = self.bus.recv(timeout=0)
                if msg is None:
                    break

                # Skip echo frames (TX echos from gs_usb / candleLight adapters)
                if not getattr(msg, "is_rx", True):
                    continue

                if len(msg.data) != 8:
                    continue

                # Feedback messages include the logical motor ID in the low 4 bits
                # of the first data byte. Use that to route feedback to the right motor.
                logical_id = msg.data[0] & 0x0F
                motor = self._motors_by_feedback.get(logical_id)
                if motor is None:
                    continue

                motor.process_feedback_frame(
                    bytes(msg.data), arbitration_id=msg.arbitration_id
                )
        except (ValueError, OSError, AttributeError):
            # Bus is closed or invalid, stop polling
            with self._polling_lock:
                self._polling_active = False

    # -----------------------
    # Background polling
    # -----------------------
    def _start_polling(self) -> None:
        """
        Start the background polling thread if needed.

        Starts a daemon thread running ``_polling_loop`` only when:
        - polling is not already active, and
        - at least one motor is registered.

        This method is idempotent for repeated calls.
        """
        with self._polling_lock:
            if self._polling_active:
                return  # Already active, do nothing

            if len(self.motors) == 0:
                return  # No motors, no need to start polling

            self._polling_active = True
            self._polling_thread = threading.Thread(
                target=self._polling_loop,
                daemon=True,  # Daemon thread will exit automatically on program shutdown
            )
            self._polling_thread.start()

    def _stop_polling(self) -> None:
        """
        Request background polling thread shutdown and wait briefly.

        Sets ``_polling_active`` to ``False`` and joins the worker thread with a
        short timeout. The polling loop checks this flag each cycle, so shutdown
        is typically fast.
        """
        with self._polling_lock:
            self._polling_active = False
            if self._polling_thread is not None:
                self._polling_thread.join(timeout=0.1)
                self._polling_thread = None

    def _polling_loop(self) -> None:
        """
        Background worker that continuously calls ``poll_feedback``.

        Loop behavior:
        - Runs while ``_polling_active`` is ``True``.
        - Exits if no motors remain registered.
        - Exits on polling exceptions (bus errors, invalid state, etc.).
        - Sleeps 1 ms per cycle to avoid CPU busy spinning.

        The inner frame-drain loop lives in ``poll_feedback`` and is non-blocking,
        so this worker remains responsive to shutdown requests.
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
        """
        Shutdown controller resources in a safe order.

        Steps:
        1. Stop background polling thread (via ``_stop_polling``).
        2. Disable all registered motors.
        3. Shutdown the CAN bus handle.

        This ensures polling is not racing against bus shutdown.
        """
        self._stop_polling()
        self.disable_all()
        self.bus.shutdown()

"""
Manual test: gs_usb lifecycle / reconnect on macOS.

Uses can.Bus directly — does NOT import damiao_motor.controller — so
controller.py's auto-patches cannot interfere with the --skip-* flags.

Usage:
    uv run python test_gs_usb_lifecycle.py [--skip-patch1] [--skip-patch2] [--skip-patch3]

Flags
-----
--skip-patch1   Do NOT apply Patch 1 (detach_kernel_driver no-op)
--skip-patch2   Do NOT apply Patch 2 (GsUsb.start skip device.reset)
--skip-patch3   Do NOT apply Patch 3 (GsUsb.stop release_interface)
"""

import sys
import time

import can

CHANNEL = 0
BITRATE = 1000000

skip_patch1 = "--skip-patch1" in sys.argv
skip_patch2 = "--skip-patch2" in sys.argv
skip_patch3 = "--skip-patch3" in sys.argv


# ── Apply patches selectively (BEFORE any gs_usb import via can.Bus) ─────────

def apply_patches(skip1: bool, skip2: bool, skip3: bool) -> None:
    try:
        import usb.core  # type: ignore[import-untyped]
        import usb.util  # type: ignore[import-untyped]
        from gs_usb.gs_usb import GsUsb as _GsUsb  # type: ignore[import-untyped]
    except ImportError:
        print("gs_usb / pyusb not installed — cannot patch")
        return

    # Patch 1: detach_kernel_driver
    if not skip1:
        _orig_detach = usb.core.Device.detach_kernel_driver
        def _safe_detach(self, interface):  # type: ignore[no-untyped-def]
            try:
                _orig_detach(self, interface)
            except usb.core.USBError:
                pass
        usb.core.Device.detach_kernel_driver = _safe_detach
        print("  Patch 1 applied: detach_kernel_driver no-op")
    else:
        print("  Patch 1 SKIPPED")

    if not skip2:
        _orig_start = _GsUsb.start
        def _patched_start(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            _orig_reset = self.gs_usb.reset
            self.gs_usb.reset = lambda: None
            try:
                _orig_start(self, *args, **kwargs)
            finally:
                self.gs_usb.reset = _orig_reset
        _GsUsb.start = _patched_start
        print("  Patch 2 applied: GsUsb.start skips device.reset()")
    else:
        print("  Patch 2 SKIPPED")

    if not skip3:
        _orig_stop = _GsUsb.stop
        def _patched_stop(self):  # type: ignore[no-untyped-def]
            _orig_stop(self)
            try:
                usb.util.release_interface(self.gs_usb, 0)
            except usb.core.USBError:
                pass
        _GsUsb.stop = _patched_stop
        print("  Patch 3 applied: GsUsb.stop releases interface")
    else:
        print("  Patch 3 SKIPPED")


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_bus() -> can.Bus:
    # Use can.Bus directly — never imports damiao_motor.core.controller
    return can.Bus(channel=CHANNEL, bustype="gs_usb", bitrate=BITRATE)


def send_frame(bus: can.Bus) -> None:
    msg = can.Message(arbitration_id=0x000, data=bytes(8), is_extended_id=False)
    bus.send(msg)


def run_test(label: str, fn) -> bool:
    print(f"\n{'─'*50}")
    print(f"  {label}")
    print(f"{'─'*50}")
    try:
        fn()
        print("  RESULT: PASS")
        return True
    except Exception as e:
        print(f"  RESULT: FAIL — {e}")
        return False


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_a_repeated_init() -> None:
    """
    Test A: repeated init in same session — simulates running the script twice.
    GsUsbBus.__init__ → GsUsb.start → device.reset() is the problematic call.
    Requires Patch 2 if device.reset() invalidates the Device object on macOS.
    """
    bus = make_bus()
    send_frame(bus)
    bus.shutdown()
    time.sleep(0.3)

    bus2 = make_bus()   # second init — fails without Patch 2 if reset causes stale handle
    send_frame(bus2)
    bus2.shutdown()


def test_b_reconnect_same_process() -> None:
    """
    Test B: within-process reconnect — same as GUI disconnect → connect.
    Requires Patch 3 so release_interface() allows reclaiming the device.
    """
    bus = make_bus()
    send_frame(bus)
    bus.shutdown()
    time.sleep(0.1)     # shorter delay — interface must be released, not timed out

    bus2 = make_bus()   # reconnect — fails without Patch 3 if interface stays claimed
    send_frame(bus2)
    bus2.shutdown()


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\ngs_usb lifecycle test  "
          f"(patch1={'ON' if not skip_patch1 else 'OFF'}, "
          f"patch2={'ON' if not skip_patch2 else 'OFF'}, "
          f"patch3={'ON' if not skip_patch3 else 'OFF'})")
    print("Applying patches (before any can.Bus import)...")
    apply_patches(skip_patch1, skip_patch2, skip_patch3)

    results = {}
    results["A: repeated init"] = run_test(
        "Test A: repeated init — make_bus/send/shutdown × 2",
        test_a_repeated_init,
    )
    results["B: reconnect same process (GUI)"] = run_test(
        "Test B: within-process reconnect — make_bus/send/shutdown × 2",
        test_b_reconnect_same_process,
    )

    print(f"\n{'═'*50}")
    print("  SUMMARY")
    print(f"{'═'*50}")
    for name, passed in results.items():
        print(f"  {'PASS' if passed else 'FAIL'}  {name}")
    print()

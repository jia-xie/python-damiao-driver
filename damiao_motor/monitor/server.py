"""Unified Flask server for the DaMiao Studio UI (Control + Monitor).

One app, one shared signal store, two modes:

* **monitor** — passive listen-only: a :class:`PassiveCanListener` decodes another
  controller's commands + the motors' feedback into the store. Never transmits.
* **control** — active: a :class:`ControlService` (DaMiaoController) connects/scans and
  drives motors; every command + feedback is pushed into the same store, so the realtime
  plots/table/cards show what we're driving.

Visualization endpoints (signals / snapshot / WS stream) read the shared store and work in
both modes. Control endpoints are gated to control mode.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple

from flask import Flask, jsonify, request, send_from_directory
from flask_sock import Sock

from damiao_motor.monitor.control import ControlService
from damiao_motor.monitor.decode import DEFAULT_FEEDBACK_OFFSET, DEFAULT_MOTOR_TYPE
from damiao_motor.monitor.listener import PassiveCanListener
from damiao_motor.monitor.service import _frame_to_log
from damiao_motor.monitor.store import SignalStore

_WEBAPP_DIST = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "gui", "webapp", "dist")
)
_MAX_POINTS_PER_TICK = 240

_DEV_PLACEHOLDER = """<!doctype html><html><head><meta charset="utf-8">
<title>DaMiao Studio</title><style>body{font-family:-apple-system,system-ui,sans-serif;
background:#0f1216;color:#c9d1d9;max-width:640px;margin:60px auto;padding:0 20px;line-height:1.6}
code{background:#1d242e;padding:2px 6px;border-radius:4px;color:#6aa3ff}</style></head><body>
<h1>DaMiao Studio</h1><p>The dashboard bundle has not been built yet.</p>
<pre><code>cd damiao_motor/gui/webapp &amp;&amp; npm install &amp;&amp; npm run build</code></pre>
<p>The REST API is live at <code>/api/status</code>.</p></body></html>"""


class Studio:
    """Holds the shared store + the active mode's data source."""

    def __init__(
        self,
        mode: str = "monitor",
        feedback_offset: int = DEFAULT_FEEDBACK_OFFSET,
        default_motor_type: str = DEFAULT_MOTOR_TYPE,
        raw_log_size: int = 4000,
    ) -> None:
        self.mode = mode  # 'monitor' | 'control'
        self.feedback_offset = feedback_offset
        self.default_motor_type = default_motor_type
        self.store = SignalStore(bus_name="bus")
        self._raw: Deque[Dict[str, Any]] = deque(maxlen=raw_log_size)
        self._raw_seq = 0
        self.listener: Optional[PassiveCanListener] = None
        self._demo_source = None
        self.control = ControlService(self.store, raw_push=self._raw_push)
        self.channel: Optional[str] = None
        self.bustype: str = "socketcan"
        self.demo = False
        self.error: Optional[str] = None

    # ------------------------------------------------------------- raw log
    def _raw_push(self, frame) -> None:
        self._raw_seq += 1
        self._raw.append(_frame_to_log(self._raw_seq, frame))

    def raw_since(
        self, since_seq: int, limit: int = 400
    ) -> Tuple[int, List[Dict[str, Any]]]:
        if not self._raw:
            return since_seq, []
        items = [r for r in self._raw if r["seq"] > since_seq]
        if len(items) > limit:
            items = items[-limit:]
        return (items[-1]["seq"] if items else since_seq), items

    # ------------------------------------------------------------- sources
    def _on_passive_frame(self, frame) -> None:
        self.store.ingest(frame)
        self._raw_push(frame)

    def connect(
        self,
        channel: str,
        bustype: str,
        bitrate: Optional[int],
        motor_type: Optional[str] = None,
        feedback_offset: Optional[int] = None,
    ) -> Dict[str, Any]:
        self.disconnect()
        self.error = None
        self.channel, self.bustype = channel, bustype
        if feedback_offset is not None:
            self.feedback_offset = feedback_offset
        if self.mode == "control":
            self.control.connect(channel, bustype, bitrate)
            found = self.control.scan(motor_type or self.default_motor_type)
            return {"motors": found}
        else:
            self.listener = PassiveCanListener(
                channel=channel,
                bustype=bustype,
                bitrate=bitrate,
                feedback_offset=self.feedback_offset,
                default_motor_type=motor_type or self.default_motor_type,
                on_frame=self._on_passive_frame,
            )
            self.listener.start()
            return {"motors": []}

    def disconnect(self) -> None:
        if self.listener is not None:
            self.listener.stop()
            self.listener = None
        if self._demo_source is not None:
            self._demo_source.stop()
            self._demo_source = None
        self.control.disconnect()

    def start_demo(self) -> None:
        from damiao_motor.monitor.demo import DemoSource

        self.demo = True
        self.channel = "demo"
        self._demo_source = DemoSource(on_frame=self._on_passive_frame, bus_name="bus")
        self._demo_source.start()

    def set_mode(self, mode: str) -> None:
        if mode not in ("monitor", "control"):
            raise ValueError("mode must be 'monitor' or 'control'")
        self.disconnect()
        self.mode = mode
        self.demo = False

    # ------------------------------------------------------------- readouts
    def status(self) -> Dict[str, Any]:
        connected = (
            (self.mode == "control" and self.control.connected)
            or (self.listener is not None)
            or (self._demo_source is not None)
        )
        return {
            "mode": self.mode,
            "connected": connected,
            "channel": self.channel,
            "bustype": self.bustype,
            "demo": self.demo,
            "listenOnly": bool(self.listener and self.listener.listen_only_applied),
            "framesSeen": self.listener.frames_seen if self.listener else self._raw_seq,
            "decodeErrors": self.listener.decode_errors if self.listener else 0,
            "feedbackOffset": self.feedback_offset,
            "defaultMotorType": self.default_motor_type,
            "registryVersion": self.store.registry_version,
            "error": self.control.error or self.error,
        }

    def signals(self) -> Dict[str, Any]:
        return {
            "signals": self.store.list_signals(),
            "pairs": self.store.pairs(),
            "motors": self.store.motor_views(),
            "version": self.store.registry_version,
        }

    def snapshot(self, ids: List[str], n: int) -> Dict[str, List[Tuple[float, float]]]:
        return {sid: self.store.series_last_n(sid, n) for sid in ids}


def _platform_defaults() -> Dict[str, Any]:
    is_mac = sys.platform == "darwin"
    return {
        "platform": sys.platform,
        "default_bustype": "gs_usb" if is_mac else "socketcan",
        "default_channel": "0" if is_mac else "can0",
    }


def create_app(studio: Studio) -> Flask:
    app = Flask(__name__)
    sock = Sock(app)

    def control_guard():
        if studio.mode != "control":
            return jsonify({"success": False, "error": "Not in control mode"}), 409
        if not studio.control.connected:
            return jsonify({"success": False, "error": "Not connected"}), 400
        return None

    # ----------------------------------------------------------- common
    @app.route("/api/status")
    def status():
        return jsonify(studio.status())

    @app.route("/api/mode", methods=["POST"])
    def set_mode():
        data = request.get_json(force=True, silent=True) or {}
        try:
            studio.set_mode(str(data.get("mode")))
        except ValueError as e:
            return jsonify({"success": False, "error": str(e)}), 400
        return jsonify({"success": True, "mode": studio.mode})

    @app.route("/api/connect", methods=["POST"])
    def connect():
        data = request.get_json(force=True, silent=True) or {}
        channel = data.get("channel", "can0")
        bustype = data.get("bustype", "socketcan")
        bitrate = data.get("bitrate")
        bitrate = int(bitrate) if bitrate not in (None, "") else None
        try:
            res = studio.connect(
                channel,
                bustype,
                bitrate,
                motor_type=data.get("motor_type"),
                feedback_offset=data.get("feedback_offset"),
            )
            return jsonify({"success": True, **res})
        except Exception as e:
            studio.error = str(e)
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/disconnect", methods=["POST"])
    def disconnect():
        studio.disconnect()
        return jsonify({"success": True})

    @app.route("/api/platform")
    def platform():
        return jsonify({"success": True, **_platform_defaults()})

    @app.route("/api/motor-types")
    def motor_types():
        from damiao_motor.monitor.decode import MONITOR_MOTOR_PRESETS

        return jsonify({"types": sorted(MONITOR_MOTOR_PRESETS.keys())})

    @app.route("/api/register-table")
    def register_table():
        return jsonify({"success": True, "registers": ControlService.register_table()})

    @app.route("/api/can-interfaces")
    def can_interfaces():
        bustype = request.args.get("bustype", "socketcan")
        interfaces: List[str] = []
        if bustype != "gs_usb":
            try:
                net = "/sys/class/net"
                if os.path.isdir(net):
                    interfaces = sorted(
                        n for n in os.listdir(net) if n.startswith("can")
                    )
            except OSError:
                pass
        return jsonify({"success": True, "interfaces": interfaces})

    # ----------------------------------------------------- visualization
    @app.route("/api/monitor/signals")
    def signals():
        return jsonify(studio.signals())

    @app.route("/api/monitor/snapshot")
    def snapshot():
        ids = [s for s in request.args.get("signals", "").split(",") if s]
        n = int(request.args.get("n", 600))
        return jsonify(studio.snapshot(ids, n))

    @sock.route("/api/monitor/stream")
    def stream(ws):
        subscribed: Dict[str, float] = {}
        rate = 30.0
        period = 1.0 / rate
        raw_enabled = False
        raw_cursor = 0
        last_version = -1

        def drain():
            nonlocal rate, period, raw_enabled
            while True:
                msg = ws.receive(timeout=0)
                if msg is None:
                    break
                try:
                    cmd = json.loads(msg)
                except (ValueError, TypeError):
                    continue
                t = cmd.get("type")
                if t == "subscribe":
                    now = time.time()
                    new = {
                        sid: subscribed.get(sid, now) for sid in cmd.get("signals", [])
                    }
                    subscribed.clear()
                    subscribed.update(new)
                elif t == "rate":
                    try:
                        rate = max(1.0, min(120.0, float(cmd.get("value", 30))))
                        period = 1.0 / rate
                    except (ValueError, TypeError):
                        pass
                elif t == "raw":
                    raw_enabled = bool(cmd.get("enabled", False))

        try:
            while True:
                drain()
                sig = studio.signals()
                if sig["version"] != last_version:
                    last_version = sig["version"]
                    ws.send(json.dumps({"type": "meta", **sig}))
                ws.send(
                    json.dumps(
                        {
                            "type": "motors",
                            "motors": sig["motors"],
                            "status": studio.status(),
                        }
                    )
                )
                batch = {}
                for sid, cursor in list(subscribed.items()):
                    pts = studio.store.series_since(sid, cursor)
                    if not pts:
                        continue
                    if len(pts) > _MAX_POINTS_PER_TICK:
                        stride = len(pts) // _MAX_POINTS_PER_TICK + 1
                        pts = pts[::stride] + [pts[-1]]
                    batch[sid] = pts
                    subscribed[sid] = pts[-1][0]
                if batch:
                    ws.send(json.dumps({"type": "samples", "data": batch}))
                if raw_enabled:
                    raw_cursor, items = studio.raw_since(raw_cursor, limit=300)
                    if items:
                        ws.send(json.dumps({"type": "raw", "frames": items}))
                time.sleep(period)
        except Exception:
            return

    # ---------------------------------------------------------- control
    @app.route("/api/control/scan", methods=["POST"])
    def control_scan():
        g = control_guard()
        if g:
            return g
        data = request.get_json(force=True, silent=True) or {}
        try:
            found = studio.control.scan(
                data.get("motor_type") or studio.default_motor_type
            )
            return jsonify({"success": True, "motors": found})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/control/motors")
    def control_motors():
        g = control_guard()
        if g:
            return g
        return jsonify({"success": True, "motors": studio.control.motors()})

    def _simple_action(motor_id, fn):
        g = control_guard()
        if g:
            return g
        try:
            fn(motor_id)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/control/motors/<int:mid>/enable", methods=["POST"])
    def c_enable(mid):
        return _simple_action(mid, studio.control.enable)

    @app.route("/api/control/motors/<int:mid>/disable", methods=["POST"])
    def c_disable(mid):
        return _simple_action(mid, studio.control.disable)

    @app.route("/api/control/motors/<int:mid>/set-zero", methods=["POST"])
    def c_zero(mid):
        return _simple_action(mid, studio.control.set_zero)

    @app.route("/api/control/motors/<int:mid>/clear-error", methods=["POST"])
    def c_clear(mid):
        return _simple_action(mid, studio.control.clear_error)

    @app.route("/api/control/motors/<int:mid>/store-parameters", methods=["POST"])
    def c_store(mid):
        return _simple_action(mid, studio.control.store_parameters)

    @app.route("/api/control/motors/<int:mid>/command", methods=["POST"])
    def c_command(mid):
        g = control_guard()
        if g:
            return g
        data = request.get_json(force=True, silent=True) or {}
        try:
            state = studio.control.command(mid, data)
            return jsonify({"success": True, "state": state})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/control/motors/<int:mid>/state")
    def c_state(mid):
        g = control_guard()
        if g:
            return g
        try:
            return jsonify({"success": True, "state": studio.control.get_state(mid)})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/control/motors/<int:mid>/registers")
    def c_get_regs(mid):
        g = control_guard()
        if g:
            return g
        try:
            return jsonify({"success": True, **studio.control.get_registers(mid)})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/control/motors/<int:mid>/registers/<int:rid>", methods=["PUT"])
    def c_set_reg(mid, rid):
        g = control_guard()
        if g:
            return g
        data = request.get_json(force=True, silent=True) or {}
        if "value" not in data:
            return jsonify({"success": False, "error": "value required"}), 400
        try:
            res = studio.control.set_register(mid, rid, data["value"])
            return jsonify({"success": True, **res})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/control/motors/<int:mid>/motor-type", methods=["PUT"])
    def c_motor_type(mid):
        g = control_guard()
        if g:
            return g
        data = request.get_json(force=True, silent=True) or {}
        mt = data.get("motor_type")
        if not mt:
            return jsonify({"success": False, "error": "motor_type required"}), 400
        try:
            studio.control.set_motor_type(mid, mt)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    # --------------------------------------------------------------- SPA
    @app.route("/")
    def index():
        idx = os.path.join(_WEBAPP_DIST, "index.html")
        return (
            send_from_directory(_WEBAPP_DIST, "index.html")
            if os.path.exists(idx)
            else _DEV_PLACEHOLDER
        )

    @app.route("/<path:path>")
    def spa(path):
        if path.startswith("api/"):
            return jsonify({"error": "not found"}), 404
        full = os.path.join(_WEBAPP_DIST, path)
        if os.path.exists(full) and os.path.isfile(full):
            return send_from_directory(_WEBAPP_DIST, path)
        idx = os.path.join(_WEBAPP_DIST, "index.html")
        return (
            send_from_directory(_WEBAPP_DIST, "index.html")
            if os.path.exists(idx)
            else _DEV_PLACEHOLDER
        )

    return app


def run_server(
    host: str = "127.0.0.1",
    port: int = 5001,
    mode: str = "monitor",
    channel: str = "can0",
    bustype: str = "socketcan",
    bitrate: Optional[int] = None,
    feedback_offset: int = 16,
    default_motor_type: str = "DM4310",
    debug: bool = False,
    demo: bool = False,
) -> None:
    """Start the unified DaMiao Studio server (blocking)."""
    studio = Studio(
        mode=mode,
        feedback_offset=feedback_offset,
        default_motor_type=default_motor_type,
    )

    if demo:
        studio.mode = "monitor"
        studio.start_demo()
    elif mode == "monitor":
        try:
            studio.connect(channel, bustype, bitrate)
        except Exception as e:
            studio.error = str(e)

    app = create_app(studio)

    print(f"Starting DaMiao Studio ({'demo' if demo else mode} mode)...")
    print(f"  open http://{host}:{port}")
    if not debug:
        logging.getLogger("werkzeug").setLevel(logging.ERROR)
    try:
        app.run(host=host, port=port, debug=debug, threaded=True)
    finally:
        studio.disconnect()

"""Flask server for the passive monitor dashboard.

Exposes a small REST surface plus a WebSocket stream (via ``flask-sock``) and serves the
built single-page app. The server is strictly passive — it only ever reads from the bus.

Routes:
    GET  /api/monitor/status               service + listener status
    GET  /api/monitor/signals              registry: signals, cmd<->fb pairs, motor views
    GET  /api/monitor/snapshot?signals=&n= last-N samples (history backfill for a panel)
    GET  /api/monitor/motor-types          known motor-type names
    POST /api/monitor/motor-type           {motorId, motorType} -> rescale decode for a motor
    WS   /api/monitor/stream               realtime samples / motors / raw frames
    GET  /                                 the SPA (built assets) or a dev placeholder
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Optional

from flask import Flask, jsonify, request, send_from_directory
from flask_sock import Sock

from damiao_motor.monitor.service import MonitorService

_WEBAPP_DIST = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "gui", "webapp", "dist")
)

# Per-tick safety cap on samples streamed per signal (decimation for very high rates).
_MAX_POINTS_PER_TICK = 240

_DEV_PLACEHOLDER = """<!doctype html><html><head><meta charset="utf-8">
<title>DaMiao Monitor</title><style>body{font-family:-apple-system,system-ui,sans-serif;
background:#0d1117;color:#c9d1d9;max-width:640px;margin:60px auto;padding:0 20px;line-height:1.6}
code{background:#161b22;padding:2px 6px;border-radius:4px;color:#79c0ff}</style></head><body>
<h1>DaMiao Monitor</h1><p>The dashboard bundle has not been built yet.</p>
<p>For development, run the Vite dev server:</p>
<pre><code>cd damiao_motor/gui/webapp &amp;&amp; npm install &amp;&amp; npm run dev</code></pre>
<p>and open the URL it prints (it proxies the API + WebSocket back here).</p>
<p>For a production bundle: <code>npm run build</code>, then reload this page.</p>
<p>The REST API is live now at <code>/api/monitor/status</code>.</p></body></html>"""


def create_app(service: MonitorService) -> Flask:
    app = Flask(__name__)
    sock = Sock(app)
    app.config["service"] = service

    # ------------------------------------------------------------------ REST
    @app.route("/api/monitor/status")
    def status():
        return jsonify(service.status())

    @app.route("/api/monitor/signals")
    def signals():
        return jsonify(service.signals())

    @app.route("/api/monitor/snapshot")
    def snapshot():
        raw = request.args.get("signals", "")
        ids = [s for s in raw.split(",") if s]
        n = int(request.args.get("n", 600))
        return jsonify(service.snapshot(ids, n))

    @app.route("/api/monitor/motor-types")
    def motor_types():
        return jsonify({"types": service.available_motor_types()})

    @app.route("/api/monitor/motor-type", methods=["POST"])
    def set_motor_type():
        data = request.get_json(force=True, silent=True) or {}
        try:
            motor_id = int(data["motorId"])
            motor_type = str(data["motorType"])
        except (KeyError, ValueError, TypeError):
            return jsonify({"success": False, "error": "motorId and motorType required"}), 400
        service.set_motor_type(motor_id, motor_type)
        return jsonify({"success": True})

    # ------------------------------------------------------------- WebSocket
    @sock.route("/api/monitor/stream")
    def stream(ws):
        subscribed: dict[str, float] = {}  # signal id -> last-sent timestamp cursor
        rate = 30.0
        raw_enabled = False
        raw_cursor = 0
        last_version = -1
        period = 1.0 / rate

        def drain_control():
            nonlocal rate, raw_enabled, period
            while True:
                msg = ws.receive(timeout=0)
                if msg is None:
                    break
                try:
                    cmd = json.loads(msg)
                except (ValueError, TypeError):
                    continue
                ctype = cmd.get("type")
                if ctype == "subscribe":
                    now = time.time()
                    new = {sid: now for sid in cmd.get("signals", [])}
                    # keep existing cursors for still-subscribed signals
                    for sid in list(new):
                        if sid in subscribed:
                            new[sid] = subscribed[sid]
                    subscribed.clear()
                    subscribed.update(new)
                elif ctype == "rate":
                    try:
                        rate = max(1.0, min(120.0, float(cmd.get("value", 30))))
                        period = 1.0 / rate
                    except (ValueError, TypeError):
                        pass
                elif ctype == "raw":
                    raw_enabled = bool(cmd.get("enabled", False))

        try:
            while True:
                drain_control()

                # registry / pairs only when it changes; motors every tick (cheap)
                sig = service.signals()
                if sig["version"] != last_version:
                    last_version = sig["version"]
                    ws.send(json.dumps({"type": "meta", **sig}))
                ws.send(json.dumps({"type": "motors", "motors": sig["motors"],
                                    "status": service.status()}))

                # sample batches for subscribed signals
                batch = {}
                for sid, cursor in list(subscribed.items()):
                    pts = service.store.series_since(sid, cursor)
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
                    raw_cursor, items = service.raw_since(raw_cursor, limit=300)
                    if items:
                        ws.send(json.dumps({"type": "raw", "frames": items}))

                time.sleep(period)
        except Exception:
            # client disconnected or socket error: end the handler cleanly
            return

    # ------------------------------------------------------------------- SPA
    @app.route("/")
    def index():
        idx = os.path.join(_WEBAPP_DIST, "index.html")
        if os.path.exists(idx):
            return send_from_directory(_WEBAPP_DIST, "index.html")
        return _DEV_PLACEHOLDER

    @app.route("/<path:path>")
    def spa(path):
        if path.startswith("api/"):
            return jsonify({"error": "not found"}), 404
        full = os.path.join(_WEBAPP_DIST, path)
        if os.path.exists(full) and os.path.isfile(full):
            return send_from_directory(_WEBAPP_DIST, path)
        # SPA client-side routing fallback
        idx = os.path.join(_WEBAPP_DIST, "index.html")
        if os.path.exists(idx):
            return send_from_directory(_WEBAPP_DIST, "index.html")
        return _DEV_PLACEHOLDER

    return app


def run_server(
    host: str = "127.0.0.1",
    port: int = 5001,
    channel: str = "can0",
    bustype: str = "socketcan",
    bitrate: Optional[int] = None,
    feedback_offset: int = 16,
    default_motor_type: str = "DM4310",
    debug: bool = False,
    demo: bool = False,
) -> None:
    """Start the passive monitor server (blocking)."""
    service = MonitorService(
        channel=channel,
        bustype=bustype,
        bitrate=bitrate,
        feedback_offset=feedback_offset,
        default_motor_type=default_motor_type,
        demo=demo,
    )
    service.start()

    app = create_app(service)

    print("Starting DaMiao Passive Monitor (listen-only)...")
    if demo:
        print("  DEMO mode: synthesizing motor traffic (no CAN bus opened)")
    print(f"  bus: {channel} ({bustype})  feedback offset: +{feedback_offset}")
    if service.error:
        print(f"  WARNING: could not open bus: {service.error}")
    elif not service.listener.listen_only_applied:
        print("  note: hardware listen-only not applied (still never transmits)")
    print(f"  open http://{host}:{port} in your browser")

    if not debug:
        logging.getLogger("werkzeug").setLevel(logging.ERROR)
    try:
        # threaded=True so the WS handler and HTTP requests run concurrently
        app.run(host=host, port=port, debug=debug, threaded=True)
    finally:
        service.stop()

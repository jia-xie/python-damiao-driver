# DaMiao Passive Monitor

A **listen-only** realtime dashboard. While another controller drives the motors on a CAN
bus, the monitor decodes **both** the commands that controller is sending **and** the
motors' feedback, and plots/tables them live. It never transmits on the bus.

## Run

```bash
# Listen on a socketcan bus that another controller is already driving
damiao monitor --channel can_arm_l

# Try it with synthetic traffic — no CAN hardware needed
damiao monitor --demo

# then open http://127.0.0.1:5001
```

Key options: `--channel`, `--bustype` (default `socketcan`), `--bitrate` (e.g. for gs_usb),
`--feedback-offset` (feedback arb id = motor id + offset; default **16** = the I2RT `p16`
scheme), `--motor-type` (default scaling, default `DM4310`), `--demo`, `--port`.

## Using the dashboard

- **Free-form widget canvas**: each panel is a widget you can **drag by its header** and
  **resize from any edge/corner**, placed anywhere on the grid. Add widgets from the
  toolbar (**Plot / Motor Table / Motor Cards / Raw CAN Log**), remove with the **×** on
  the widget header. Layout + plot contents persist across reloads (**Reset** restores the
  default layout).
- **Drag** a signal from the left sidebar onto a **Plot** widget to chart it. Drop a `cmd.*`
  signal onto the plot already showing its `fb.*` to **overlay** them (dashed = command,
  solid = feedback).
- Per-motor **motor-type** can be overridden in the cards (rescales decode).

## How it stays passive

- The `monitor` package never imports or calls anything that transmits; it only ever calls
  `bus.recv`. (`tests/test_monitor.py` asserts this.)
- On socketcan it also sets `CAN_RAW_LISTEN_ONLY` on the socket (best-effort defense in
  depth). On a separate socketcan socket it sees all bus traffic without stealing frames
  from the running controller.

## Dev workflow (changing the UI)

The dashboard is a Vite/React/TS app in `gui/webapp`. The built bundle in
`gui/webapp/dist/` is committed so end users need no Node toolchain. To develop:

```bash
cd damiao_motor/gui/webapp
npm install
npm run dev            # Vite dev server on :5173, proxies /api + WS to the monitor
# in another shell:
damiao monitor --demo  # or --channel <bus>
# open the Vite URL (http://localhost:5173)

npm run build          # rebuild dist/ before committing UI changes
```

## Test checklist

### A. Offline (no hardware — runs anywhere)
1. `pytest tests/test_monitor.py` — command/feedback decode round-trips + the
   never-transmit assertion (10 tests).
2. `python -m build` then confirm the wheel ships the UI + package:
   `unzip -l dist/*.whl | grep -E "webapp/dist/index.html|monitor/server.py"`.
3. `damiao monitor --demo` → open the URL: signals appear, drag `cmd.pos`+`fb.pos` onto a
   plot and see the overlay track; cards + table update; add a Raw CAN Log panel and watch
   frames stream; reload and confirm layout/plots persist.

### B. On xdof_linearbot (real CAN)
4. **Idle bus, no crash:** with no controller running,
   `damiao monitor --channel can_arm_l --host 0.0.0.0` → dashboard loads, top bar shows
   `listen-only`, signal list empty (idle bus invents nothing).
5. **Passivity (do this any time it runs):** in another shell
   `watch -n1 'ip -s link show can_arm_l | sed -n 5,6p'` → TX packets stay **0** while the
   monitor runs. (Verified during development: opened the bus, `listen_only_applied=True`,
   TX stayed 0.)
6. **Live decode:** start the real controller (FlowBase / LinearRail desktop launcher) or
   a benign sender → on the monitor:
   - signals auto-appear per motor; `cmd`↔`fb` pairs link;
   - drag `cmd.pos` onto the `fb.pos` plot → overlay tracks (dashed cmd vs solid actual);
   - Motor Table shows live commanded + actual columns; Cards update; Raw CAN Log streams
     decoded MIT/POS_VEL/feedback frames.
7. **Right scaling:** if a motor reads with the wrong range (e.g. a base `DM4310V` uses
   ±π rad), set its type in the card dropdown and confirm values correct.
8. **Feedback scheme:** if no feedback signals appear but commands do, the bus may not use
   the `p16` (+16) feedback-id scheme — rerun with the correct `--feedback-offset`.
9. **Smoothness:** with all arm motors streaming at control rate, plots stay smooth and the
   time window scrolls without growing lag.
10. **Coexistence:** the active controller is unaffected (the monitor only reads), and
    `damiao gui` still works as before on its own run.

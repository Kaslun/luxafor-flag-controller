# Beacon — Luxafor Flag 2 status bridge

Beacon drives a Luxafor Flag 2 desk light from local signals — automatic
call detection (mic capture), scheduled routines, and manual override —
so the flag reflects your real status. Local-only, per-user, single
machine. No cloud, no server, no admin rights.

One bundled exe: headless engine + a localhost web UI + a tray icon, in
a single process.

## Architecture

- **Engine** (`engine/`) owns the USB/HID handle, runs a pure resolver,
  reads the Windows mic-capture registry, and serves a localhost FastAPI.
- **FastAPI** (`engine/app.py`) exposes state/commands as JSON and serves
  the built React UI.
- **Tray** (`engine/tray.py`) — pystray icon: glance + quick actions.
- **SQLite** (`engine/history.py`) in `%APPDATA%\Beacon\` logs transitions.
- **UI** (`ui/`) — Vite + React + Tailwind, built to static files.

The resolver (`engine/resolver.py`) and the State contract
(`engine/state.py`) are the single source of truth the UI and tray read.

## Development

Engine:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
pytest
python -m engine          # boots engine + API + tray on 127.0.0.1:54741
```

UI (separate terminal, proxies /api to the running engine):

```powershell
cd ui
npm ci
npm run dev               # http://localhost:5173
```

## Build

```powershell
./scripts/build.ps1        # ui build -> dist/beacon.exe
```

## Notes

- Device layer is raw `hidapi`. The validated write report is 8 bytes
  `[0x00, 0x01, 0xFF, R, G, B, 0x00, 0x00]`, written twice.
- Call detection reads the Windows consent-store mic-capture registry,
  not audio volume.
- The localhost API has no auth in v1 — loopback-only, single user, by
  design.
- Updates are manual-replace via GitHub releases; Beacon never
  self-overwrites.

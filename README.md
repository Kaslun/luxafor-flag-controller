# Beacon — Luxafor Flag 2 status bridge

Beacon drives a Luxafor Flag 2 desk light from local signals — custom
event triggers (mic in a call, a specific app on the mic, webcam in use,
screen locked), scheduled routines, and manual override — so the flag
reflects your real status. Local-only, per-user, single machine. No
cloud, no server, no admin rights.

One bundled exe: headless engine + a localhost web UI + a tray icon, in
a single process.

## For users (running Beacon)

1. **Download** `beacon.exe` from the
   [latest release](https://github.com/Kaslun/luxafor-flag-controller/releases).
   No installer, no admin rights, nothing else to download.
2. **Run it.** Windows SmartScreen may show *"Windows protected your PC"*
   because the exe isn't code-signed yet. Click **More info → Run anyway**.
   (This is expected for an unsigned app; signing is planned.)
3. A **tray icon** appears and the status window opens in your browser at
   `http://127.0.0.1:54741`. The tray icon's color always mirrors the flag.
4. In **Settings**, turn on **Start with Windows** so Beacon launches
   automatically each time you sign in — set it and forget it.
5. **First-run conflict:** if the original Luxafor app is installed, both
   apps fight over the flag and it flickers. Beacon detects this and walks
   you through quitting it and removing it from startup. Do that once and
   Beacon has the flag to itself.

That's the whole end-user path — everything below is for developers.

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

Local one-off build (needs the venv active so `pyinstaller` resolves):

```powershell
.venv\Scripts\Activate.ps1
./scripts/build.ps1        # ui build + icon -> dist/beacon.exe + dist/version.json
```

## Releasing

CI does the build — you don't run PyInstaller by hand for a release:

1. Bump `__version__` in `engine/version.py` (e.g. `0.1.1`).
2. Commit, then tag and push:
   ```powershell
   git tag v0.1.1
   git push origin v0.1.1
   ```
3. The **Release** workflow (`.github/workflows/release.yml`) builds
   `beacon.exe` on a Windows runner and publishes a GitHub Release with
   `beacon.exe` and `version.json` attached. The tag must match
   `engine/version.py` or the build fails on purpose.

The in-app updater fetches `version.json` from the release CDN (not the
GitHub API, to avoid the shared-NAT rate limit) and, if a newer version
exists, shows a non-blocking banner linking to the releases page. Beacon
never self-overwrites — users download and run the new exe.

`.github/workflows/ci.yml` runs the tests and a UI build on every push/PR
to `main`.

## Notes

- Device layer is raw `hidapi`. The validated write report is 8 bytes
  `[0x00, 0x01, 0xFF, R, G, B, 0x00, 0x00]`, written twice.
- Mic/webcam triggers read the Windows consent-store capture registry,
  not audio/video volume. Each trigger carries a priority; the highest
  active one wins, beating a manual override only above priority 50.
- The localhost API has no auth in v1 — loopback-only, single user, by
  design.
- Updates are manual-replace via GitHub releases; Beacon never
  self-overwrites.
- **Auto-start** registers the per-user `Run` key
  (`HKCU\...\CurrentVersion\Run`) — no admin needed. Toggle it from
  Settings; see `engine/autostart.py`.
- **SmartScreen / signing:** the exe is currently unsigned, so first-run
  shows a SmartScreen prompt. Code-signing (which also clears SmartScreen)
  is a pre-rollout step, not yet done.

"""Beacon entrypoint: boot the engine, serve the API+UI, raise the tray.

Single process: uvicorn (with the engine tick loop running as a task on
its event loop) on the main thread, the pystray icon on a daemon thread.

Behavior on launch:
  - Single instance: a named mutex makes the guard atomic. If Beacon is
    already running, hand off to it — focus the open tab if one is connected,
    else open one — and exit. Double-clicking the exe never spawns a second
    tray icon on another port.
  - Browser: open the dashboard on startup, but skip it (and instead nudge
    the existing tab forward) if a UI tab is already connected — so a
    reconnecting tab after a port rebind doesn't leave a duplicate.

The server binds loopback on a default port, falling back to the next few
ports if taken; the chosen port is recorded in an instance lock file so the
single-instance check and the tray's "Open Beacon" both find it.
"""

from __future__ import annotations

import json
import socket
import threading
import webbrowser
from urllib.request import Request, urlopen

import uvicorn

from engine import singleinstance
from engine.app import create_app
from engine.logging_setup import setup_logging
from engine.loop import BeaconEngine
from engine.paths import app_dir
from engine.tray import start_tray

DEFAULT_PORT = 54741
PORT_TRIES = 10
HOST = "127.0.0.1"


def _lock_file():
    return app_dir() / "instance.json"


def _existing_instance_port() -> int | None:
    """If another Beacon is alive, return its port; else None (clearing a
    stale lock)."""
    lf = _lock_file()
    try:
        data = json.loads(lf.read_text(encoding="utf-8"))
        port = int(data["port"])
    except (OSError, ValueError, KeyError):
        return None
    try:
        with urlopen(f"http://{HOST}:{port}/api/state", timeout=0.75) as r:
            if r.status == 200:
                return port
    except Exception:
        pass
    # stale lock — owner is gone
    try:
        lf.unlink()
    except OSError:
        pass
    return None


def _write_lock(port: int) -> None:
    try:
        _lock_file().write_text(json.dumps({"port": port}), encoding="utf-8")
    except OSError:
        pass


def _clear_lock() -> None:
    try:
        _lock_file().unlink()
    except OSError:
        pass


def _pick_port() -> int:
    for offset in range(PORT_TRIES):
        port = DEFAULT_PORT + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((HOST, port))
                return port
            except OSError:
                continue
    raise SystemExit(
        f"No free port in {DEFAULT_PORT}..{DEFAULT_PORT + PORT_TRIES - 1}"
    )


def _client_alive(port: int) -> bool:
    try:
        with urlopen(f"http://{HOST}:{port}/api/clients", timeout=0.75) as r:
            return bool(json.loads(r.read()).get("alive"))
    except Exception:
        return False


def _handoff_to_existing(port: int) -> None:
    """A second launch: if a tab is already open, nudge it forward instead of
    spawning a duplicate; otherwise open one."""
    if _client_alive(port):
        try:
            urlopen(Request(f"http://{HOST}:{port}/api/focus", method="POST"), timeout=0.75)
        except Exception:
            pass
    else:
        try:
            webbrowser.open(f"http://{HOST}:{port}/", new=0)
        except Exception:
            pass


def _open_dashboard_when_idle(engine, url: str, grace: float = 3.5) -> None:
    """Open the dashboard on startup — but only if no UI tab is already open.

    A previously-open tab reconnects within a poll interval when the engine
    (re)starts on the same port; waiting one grace window lets us detect it and
    skip opening a duplicate. If a tab is there, nudge it forward instead.
    """
    def _go():
        try:
            if engine.client_alive():
                engine.request_focus()
            else:
                webbrowser.open(url)
        except Exception:
            pass

    threading.Timer(grace, _go).start()


def main() -> None:
    log = setup_logging()
    log.info("Beacon starting")

    # Single-instance guard (atomic). If another Beacon already holds the
    # mutex, hand off to it: open its dashboard and exit.
    if not singleinstance.acquire():
        existing = _existing_instance_port()
        log.info("another instance is running (port=%s); opening it", existing)
        if existing is not None:
            _handoff_to_existing(existing)
        return

    engine = BeaconEngine()
    port = _pick_port()
    engine.state.port = port
    url = f"http://{HOST}:{port}/"
    _write_lock(port)

    app = create_app(engine)
    start_tray(engine)
    # Open the dashboard on startup — but skip it if a UI tab is already open
    # (e.g. a previous tab that reconnects when we rebind the same port), so we
    # don't drop a duplicate tab into the user's focused window.
    _open_dashboard_when_idle(engine, url)

    log.info("serving on %s", url)
    try:
        uvicorn.run(app, host=HOST, port=port, log_level="warning", log_config=None)
    except KeyboardInterrupt:
        pass
    except Exception:
        log.exception("server crashed")
        raise
    finally:
        _clear_lock()
        log.info("Beacon stopped")


if __name__ == "__main__":
    main()

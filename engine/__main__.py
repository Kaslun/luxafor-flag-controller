"""Beacon entrypoint: boot the engine, serve the API+UI, raise the tray.

Single process: uvicorn (with the engine tick loop running as a task on
its event loop) on the main thread, the pystray icon on a daemon thread.

Behavior on launch:
  - Single instance: a named mutex makes the guard atomic. If Beacon is
    already running, we just open its dashboard and exit — double-clicking
    the exe (or shortcut) never spawns a second tray icon on another port.
  - Browser: open the dashboard automatically on a normal manual launch,
    on first-ever run, or with ``--show`` (post-update relaunch). Only a
    sign-in autostart launch (``--autostart``) stays quietly in the tray.

The server binds loopback on a default port, falling back to the next few
ports if taken; the chosen port is recorded in an instance lock file so the
single-instance check and the tray's "Open Beacon" both find it.
"""

from __future__ import annotations

import json
import socket
import sys
import threading
import webbrowser
from urllib.request import urlopen

import uvicorn

from engine import singleinstance
from engine.app import create_app
from engine.logging_setup import setup_logging
from engine.loop import BeaconEngine
from engine.paths import app_dir, config_path
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


def _open_browser_soon(url: str, delay: float = 1.5) -> None:
    def _go():
        try:
            webbrowser.open(url)
        except Exception:
            pass

    threading.Timer(delay, _go).start()


def main() -> None:
    log = setup_logging()
    log.info("Beacon starting")

    # Single-instance guard (atomic). If another Beacon already holds the
    # mutex, hand off to it: open its dashboard and exit.
    if not singleinstance.acquire():
        existing = _existing_instance_port()
        log.info("another instance is running (port=%s); opening it", existing)
        if existing is not None:
            try:
                # new=0 asks the browser to reuse an existing window/tab where
                # it can rather than always spawning a new one
                webbrowser.open(f"http://{HOST}:{existing}/", new=0)
            except Exception:
                pass
        return

    args = sys.argv[1:]
    autostart_launch = "--autostart" in args
    force_show = "--show" in args
    # First-ever run? (decide before the engine creates the config file)
    first_run = not config_path().exists()

    engine = BeaconEngine()
    port = _pick_port()
    engine.state.port = port
    url = f"http://{HOST}:{port}/"
    _write_lock(port)

    app = create_app(engine)
    start_tray(engine)
    # Open the dashboard on startup — every launch, including a sign-in
    # autostart launch (a second launch reuses this instance, above, rather
    # than starting another). force_show/first_run/autostart_launch are kept
    # for logging only.
    _ = (force_show, first_run, autostart_launch)
    _open_browser_soon(url)

    log.info("serving on %s (first_run=%s show=%s)", url, first_run, force_show)
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

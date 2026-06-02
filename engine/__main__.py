"""Beacon entrypoint: boot the engine, serve the API+UI, raise the tray.

Single process: uvicorn (with the engine tick loop running as a task on
its event loop) on the main thread, the pystray icon on a daemon thread.

The server binds loopback on a default port, falling back to the next few
ports if it's taken; the chosen port is stored on State so the tray's
"Open Beacon" knows where to point.

Frozen/windowed notes (PyInstaller --noconsole): ``sys.stdout`` and
``sys.stderr`` are ``None``. uvicorn's default logging config references
``ext://sys.stdout`` / ``ext://sys.stderr``; reconfiguring logging onto
those None streams raises during startup, which previously exited the
process silently. We pass ``log_config=None`` so uvicorn leaves logging
alone (we have our own file logger), and we never let an exception exit
without recording it.
"""

from __future__ import annotations

import socket
import threading
import webbrowser

import uvicorn

from engine.app import create_app
from engine.logging_setup import setup_logging
from engine.loop import BeaconEngine
from engine.tray import start_tray

DEFAULT_PORT = 54741
PORT_TRIES = 10
HOST = "127.0.0.1"


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
    """Open the dashboard shortly after the server starts accepting.

    Gives a launching user an immediate visible window instead of just a
    tray icon. Best-effort; failure is harmless.
    """

    def _go():
        try:
            webbrowser.open(url)
        except Exception:
            pass

    threading.Timer(delay, _go).start()


def main() -> None:
    log = setup_logging()
    log.info("Beacon starting")

    engine = BeaconEngine()
    port = _pick_port()
    engine.state.port = port
    url = f"http://{HOST}:{port}/"

    app = create_app(engine)

    # tray on a daemon thread; engine loop runs inside uvicorn's lifespan
    start_tray(engine)
    _open_browser_soon(url)

    log.info("serving on %s", url)
    try:
        # log_config=None: keep our file logger; don't let uvicorn try to
        # attach handlers to the None stdout/stderr of a windowed exe.
        uvicorn.run(app, host=HOST, port=port, log_level="warning", log_config=None)
    except KeyboardInterrupt:
        pass
    except Exception:
        log.exception("server crashed")
        raise
    finally:
        log.info("Beacon stopped")


if __name__ == "__main__":
    main()

"""Beacon entrypoint: boot the engine, serve the API+UI, raise the tray.

Single process: uvicorn (with the engine tick loop running as a task on
its event loop) on the main thread, the pystray icon on a daemon thread.

The server binds loopback on a default port, falling back to the next few
ports if it's taken; the chosen port is stored on State so the tray's
"Open Beacon" knows where to point.
"""

from __future__ import annotations

import socket
import sys

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


def main() -> None:
    log = setup_logging()
    log.info("Beacon starting")

    engine = BeaconEngine()
    port = _pick_port()
    engine.state.port = port

    app = create_app(engine)

    # tray on a daemon thread; engine loop runs inside uvicorn's lifespan
    start_tray(engine)

    log.info("serving on http://%s:%d", HOST, port)
    try:
        uvicorn.run(app, host=HOST, port=port, log_level="warning")
    except KeyboardInterrupt:
        pass
    finally:
        log.info("Beacon stopped")
        sys.exit(0)


if __name__ == "__main__":
    main()

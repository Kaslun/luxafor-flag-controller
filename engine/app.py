"""The localhost FastAPI: state + commands + the static React UI.

Bound to loopback only. **No auth in v1** — this is a deliberate decision,
not an oversight: the server listens on 127.0.0.1 only, serves a single
local user on one machine, has no network exposure, and handles no
sensitive data. Do not add token/login plumbing without a real multi-user
requirement (there isn't one — see build spec scope).

The UI is served from the built ``ui/dist`` directory. When running from a
PyInstaller one-file bundle, that directory is unpacked under
``sys._MEIPASS``; otherwise it's the repo's ``ui/dist``.
"""

from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from engine.config import ConfigError, config_from_dict
from engine.effects import as_payload as effects_payload
from engine.logging_setup import get_logger
from engine.palette import as_payload as palette_payload
from engine.version import __version__

log = get_logger()


# ----------------------------------------------------------- request models

class OverrideBody(BaseModel):
    color: str
    duration_minutes: int | None = None
    effect: dict | None = None


class ConfigBody(BaseModel):
    routines: list[dict] = []
    settings: dict = {}


# ----------------------------------------------------------- static dir

def _static_dir() -> Path | None:
    """Locate the built UI, bundled or in-repo. None if not built yet."""
    meipass = getattr(sys, "_MEIPASS", None)
    candidates = []
    if meipass:
        candidates.append(Path(meipass) / "ui" / "dist")
    here = Path(__file__).resolve().parent
    candidates.append(here.parent / "ui" / "dist")
    for c in candidates:
        if c.is_dir() and (c / "index.html").exists():
            return c
    return None


# ----------------------------------------------------------- app factory

def create_app(engine) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        # run the engine tick loop on uvicorn's event loop
        task = asyncio.create_task(engine.run())
        try:
            yield
        finally:
            engine.stop()
            try:
                await asyncio.wait_for(task, timeout=5.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                task.cancel()
            engine.shutdown()

    app = FastAPI(
        title="Beacon",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )

    @app.get("/api/state")
    def get_state():
        return engine.state.snapshot()

    @app.get("/api/config")
    def get_config():
        return engine.config.to_dict()

    @app.put("/api/config")
    def put_config(body: ConfigBody):
        try:
            cfg = config_from_dict(body.model_dump())
        except ConfigError as e:
            raise HTTPException(status_code=400, detail=str(e))
        engine.replace_config(cfg)
        return engine.config.to_dict()

    @app.get("/api/palette")
    def get_palette():
        return palette_payload()

    @app.get("/api/effects")
    def get_effects():
        return effects_payload()

    @app.post("/api/override")
    def post_override(body: OverrideBody):
        try:
            ov = engine.set_override(body.color, body.duration_minutes, body.effect)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return ov

    @app.delete("/api/override")
    def delete_override():
        engine.clear_override()
        return {"ok": True}

    @app.post("/api/pause")
    def post_pause():
        engine.set_paused(True)
        return {"paused": True}

    @app.delete("/api/pause")
    def delete_pause():
        engine.set_paused(False)
        return {"paused": False}

    @app.post("/api/conflict/recheck")
    def post_recheck():
        return {"conflict_detected": engine.recheck_conflict()}

    @app.post("/api/update/recheck")
    def post_update_recheck():
        # synchronous network check; runs in FastAPI's threadpool (def, not async)
        return {"update_available": engine.recheck_update()}

    @app.post("/api/autostart")
    def post_autostart():
        return {"autostart_enabled": engine.set_autostart(True)}

    @app.delete("/api/autostart")
    def delete_autostart():
        return {"autostart_enabled": engine.set_autostart(False)}

    # static UI — mounted last so /api/* always wins.
    static = _static_dir()
    if static is not None:
        app.mount("/", StaticFiles(directory=str(static), html=True), name="ui")
        log.info("serving UI from %s", static)
    else:
        @app.get("/")
        def no_ui():
            return JSONResponse(
                {
                    "detail": "UI not built. Run `npm run build` in ui/, "
                    "or use the Vite dev server."
                },
                status_code=503,
            )
        log.warning("UI not built; serving API only")

    return app

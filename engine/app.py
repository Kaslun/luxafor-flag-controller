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

import os

from engine import mic, webcam
from engine.config import ConfigError, config_from_dict, triggers_meta
from engine.effects import as_payload as effects_payload
from engine.logging_setup import get_logger
from engine.palette import as_payload as palette_payload
from engine.paths import log_path
from engine.version import __version__

log = get_logger()


# ----------------------------------------------------------- request models

class OverrideBody(BaseModel):
    color: str
    duration_minutes: int | None = None
    effect: dict | None = None


class PreviewBody(BaseModel):
    color: str
    effect: dict | None = None


class ConfigBody(BaseModel):
    routines: list[dict] = []
    triggers: list[dict] = []
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

        def _on_done(t: asyncio.Task):
            # the loop should only end on shutdown; if it ends otherwise,
            # make the reason visible instead of letting it vanish
            if t.cancelled():
                return
            exc = t.exception()
            if exc is not None:
                log.error("engine loop task ended unexpectedly: %r", exc)

        task.add_done_callback(_on_done)
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

    @app.middleware("http")
    async def no_cache_html(request, call_next):
        # Vite asset filenames are content-hashed (safe to cache forever),
        # but index.html must never be cached or an in-place update leaves
        # the browser on the old bundle. Force it to revalidate.
        resp = await call_next(request)
        path = request.url.path
        if path == "/" or path.endswith(".html"):
            resp.headers["Cache-Control"] = "no-store, must-revalidate"
        return resp

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

    @app.get("/api/triggers/meta")
    def get_triggers_meta():
        return triggers_meta()

    @app.get("/api/signals")
    def get_signals():
        # currently-detected capturers, so the mic_app editor can offer a
        # live "detected now" picker instead of blind typing
        try:
            return {
                "mic_capturers": mic.mic_capturers(),
                "webcam_capturers": webcam.webcam_capturers(),
            }
        except Exception as e:  # pragma: no cover - defensive
            log.debug("signals read failed: %s", e)
            return {"mic_capturers": [], "webcam_capturers": []}

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

    @app.post("/api/preview")
    def post_preview(body: PreviewBody):
        try:
            return engine.set_preview(body.color, body.effect)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.delete("/api/preview")
    def delete_preview():
        engine.clear_preview()
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

    @app.post("/api/update/apply")
    def post_update_apply():
        # downloads + verifies, then the process exits ~1s later to let the
        # swap script replace the exe and relaunch it
        try:
            return engine.apply_update()
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/logs/open")
    def post_open_logs():
        # opens beacon.log in the default text editor for diagnostics
        p = log_path()
        try:
            os.startfile(str(p))  # type: ignore[attr-defined]  # Windows only
        except AttributeError:
            raise HTTPException(status_code=501, detail="not supported on this OS")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        return {"opened": str(p)}

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

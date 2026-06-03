"""In-place auto-update for the packaged exe.

NOTE — deliberate reversal of the original "never self-replace" spec
decision, scoped to internal distribution. The build spec chose manual
replace because a running exe can't overwrite itself on Windows and
self-replacing exes can trip endpoint security. For an internal rollout we
accept that trade for one-click updates; code-signing is the eventual
mitigation. The mechanism below downloads the new exe, verifies its
checksum, then hands off to a tiny detached script that waits for this
process to exit, swaps the file, and relaunches — so we never try to
overwrite a locked, running image.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import httpx

from engine.logging_setup import get_logger
from engine.paths import app_dir

log = get_logger()


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def current_exe() -> Path:
    return Path(sys.executable)


def _staged_path() -> Path:
    return app_dir() / "beacon-new.exe"


def download(url: str, sha256: str | None = None) -> Path:
    """Download the new exe to AppData and verify its checksum. Raises on
    network error or checksum mismatch."""
    dest = _staged_path()
    h = hashlib.sha256()
    with httpx.stream("GET", url, follow_redirects=True, timeout=120.0) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_bytes(65536):
                f.write(chunk)
                h.update(chunk)
    if sha256 and h.hexdigest().lower() != sha256.lower():
        try:
            dest.unlink()
        except OSError:
            pass
        raise RuntimeError("downloaded update failed checksum verification")
    log.info("update downloaded and verified -> %s", dest)
    return dest


_SWAP_TEMPLATE = """@echo off
setlocal enableextensions
:waitloop
tasklist /FI "PID eq {pid}" 2>NUL | find "{pid}" >NUL
if not errorlevel 1 (
  timeout /t 1 /nobreak >NUL
  goto waitloop
)
set /a tries=0
:movel
move /Y "{new}" "{target}" >NUL 2>&1
if errorlevel 1 (
  set /a tries+=1
  if %tries% LSS 15 (
    timeout /t 1 /nobreak >NUL
    goto movel
  )
)
start "" "{target}" --show
del "%~f0"
"""


def build_swap_script(pid: int, new_exe: Path, target_exe: Path) -> str:
    """The batch that waits for our PID to exit, swaps the exe, relaunches."""
    return _SWAP_TEMPLATE.format(pid=pid, new=str(new_exe), target=str(target_exe))


def launch_swap(pid: int, new_exe: Path, target_exe: Path) -> None:
    """Write the swap script and spawn it detached so it outlives us."""
    script = app_dir() / "beacon-update.bat"
    script.write_text(build_swap_script(pid, new_exe, target_exe), encoding="ascii")
    DETACHED = 0x00000008  # DETACHED_PROCESS
    NO_WINDOW = 0x08000000  # CREATE_NO_WINDOW
    subprocess.Popen(
        ["cmd", "/c", str(script)],
        creationflags=DETACHED | NO_WINDOW,
        close_fds=True,
    )
    log.info("update swap script launched; exiting for replacement")


def apply(update_info: dict) -> dict:
    """Download + verify the update and launch the swap. Caller exits next.

    Returns a small status dict. Raises on any failure so the API surfaces
    it instead of silently doing nothing.
    """
    if not is_frozen():
        raise RuntimeError("auto-update is only available in the installed app")
    if not update_info or not update_info.get("download_url"):
        raise RuntimeError("no update download is available")
    new_exe = download(update_info["download_url"], update_info.get("sha256"))
    launch_swap(os.getpid(), new_exe, current_exe())
    return {"ok": True, "version": update_info.get("version")}

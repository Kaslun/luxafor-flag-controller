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


# Notes on the script:
#  - No PID/tasklist wait: a running exe is locked, so `move /Y` simply fails
#    until Beacon's processes (Python child AND the PyInstaller bootloader
#    parent) have exited and released the file. We just retry the move until
#    the source is gone — which is also simpler/more robust than parsing
#    tasklist output in a console-less process.
#  - Delays use `ping`, not `timeout`: `timeout` needs console input and
#    fails in a detached/no-console process.
#  - The counter is tested on a single-line `if` (re-parsed on each goto) to
#    avoid the %var% delayed-expansion trap inside ( ) blocks.
_SWAP_TEMPLATE = """@echo off
setlocal
set "SRC={new}"
set "DST={target}"
set /a tries=0
:movel
move /Y "%SRC%" "%DST%" >NUL 2>NUL
if not exist "%SRC%" goto done
set /a tries+=1
if %tries% GEQ 90 goto done
ping -n 2 127.0.0.1 >NUL
goto movel
:done
start "" "%DST%" --show
del "%SRC%" >NUL 2>NUL
del "%~f0" >NUL 2>NUL
"""


def build_swap_script(pid: int, new_exe: Path, target_exe: Path) -> str:
    """The batch that swaps the exe once Beacon exits, then relaunches it.

    ``pid`` is accepted for API stability but no longer used — the move-retry
    loop waits out the file lock directly.
    """
    return _SWAP_TEMPLATE.format(new=str(new_exe), target=str(target_exe))


def launch_swap(pid: int, new_exe: Path, target_exe: Path) -> None:
    """Write the swap script and spawn it fully detached so it outlives us.

    DETACHED_PROCESS alone gives the child no console at all — no flashing
    window — and it keeps running after this process exits.
    """
    script = app_dir() / "beacon-update.bat"
    script.write_text(build_swap_script(pid, new_exe, target_exe), encoding="ascii")
    DETACHED_PROCESS = 0x00000008
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    subprocess.Popen(
        ["cmd", "/c", str(script)],
        creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
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

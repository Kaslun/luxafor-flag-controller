"""Self-update: swap-script generation and guard rails (no network/process)."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine import selfupdate


def test_swap_script_contains_paths_and_relaunch():
    s = selfupdate.build_swap_script(
        1234, Path(r"C:\new\beacon-new.exe"), Path(r"C:\app\beacon.exe")
    )
    assert r"C:\new\beacon-new.exe" in s
    assert r"C:\app\beacon.exe" in s
    assert "--show" in s               # relaunch opens the dashboard
    assert "move /Y" in s              # swaps the file
    assert "ping" in s                 # console-less delay (not `timeout`)
    assert 'del "%~f0"' in s           # script removes itself
    # clears PyInstaller one-file relaunch markers before relaunch, so the new
    # exe doesn't inherit and reuse the old (deleted) _MEI extraction dir
    assert 'set "_MEIPASS2="' in s
    # the clears must come before the relaunch line
    assert s.index('set "_MEIPASS2="') < s.index('start ""')


def test_apply_refuses_when_not_frozen():
    # tests run from source (not a PyInstaller bundle), so auto-update is off
    with pytest.raises(RuntimeError, match="installed app"):
        selfupdate.apply({"download_url": "http://x/beacon.exe", "version": "9.9.9"})


def test_apply_requires_download_url(monkeypatch):
    monkeypatch.setattr(selfupdate, "is_frozen", lambda: True)
    with pytest.raises(RuntimeError, match="no update download"):
        selfupdate.apply({"version": "9.9.9"})

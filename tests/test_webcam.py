"""Webcam-capture detection — mirrors test_mic against the webcam consent key."""

from __future__ import annotations

import pytest

from engine import webcam


@pytest.mark.parametrize(
    "start,stop,expected",
    [
        (132000000000000000, 0, True),
        (132000000000000000, 132000000001, False),
        (0, 0, False),
        (None, None, False),
        (132000000000000000, None, True),
    ],
)
def test_cam_active_truth_table(start, stop, expected):
    assert webcam._cam_active(start, stop) is expected


class FakeKey:
    def __init__(self, subkeys: dict, values: dict | None = None):
        self.subkeys = subkeys
        self.values = values or {}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeWinreg:
    HKEY_CURRENT_USER = "HKCU"

    def __init__(self, root: FakeKey):
        self._root = root

    def OpenKey(self, _root, path):
        node = self._root
        for part in path.split("\\"):
            if not part:
                continue
            if part not in node.subkeys:
                raise FileNotFoundError(path)
            node = node.subkeys[part]
        return node

    def EnumKey(self, key, i):
        names = list(key.subkeys.keys())
        if i >= len(names):
            raise OSError("no more subkeys")
        return names[i]

    def QueryValueEx(self, key, name):
        if name not in key.values:
            raise FileNotFoundError(name)
        return (key.values[name], 1)


def _build_tree():
    zoom = FakeKey({}, {"LastUsedTimeStart": 132_500, "LastUsedTimeStop": 0})
    obs = FakeKey({}, {"LastUsedTimeStart": 100, "LastUsedTimeStop": 200})
    teams = FakeKey({}, {"LastUsedTimeStart": 132_000, "LastUsedTimeStop": 0})
    nonpackaged = FakeKey({"Zoom.exe": zoom, "obs64.exe": obs})
    cam = {"MSTeams_xyz": teams, "NonPackaged": nonpackaged}

    root = FakeKey({})
    node = root
    for part in webcam._CAM_BASE.split("\\"):
        child = FakeKey({})
        node.subkeys[part] = child
        node = child
    node.subkeys.update(cam)
    return root


def test_webcam_capturers_collects_packaged_and_nonpackaged(monkeypatch):
    fake = FakeWinreg(_build_tree())
    monkeypatch.setattr(webcam, "winreg", fake)
    monkeypatch.setattr(webcam, "_IS_WINDOWS", True)

    caps = set(webcam.webcam_capturers())
    assert "MSTeams_xyz" in caps
    assert "Zoom.exe" in caps
    assert "obs64.exe" not in caps  # stopped
    assert webcam.webcam_in_use() is True


def test_webcam_false_when_no_base_key(monkeypatch):
    empty = FakeWinreg(FakeKey({}))
    monkeypatch.setattr(webcam, "winreg", empty)
    monkeypatch.setattr(webcam, "_IS_WINDOWS", True)
    assert webcam.webcam_capturers() == []
    assert webcam.webcam_in_use() is False

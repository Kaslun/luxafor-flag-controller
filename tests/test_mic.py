"""Mic-capture detection — the active-stream truth table and registry walk.

``mic_capturers`` reads the Windows registry, so on any platform we drive
it through a fake winreg that models the consent-store layout: a tree of
keys, each app key carrying LastUsedTimeStart / LastUsedTimeStop values.
"""

from __future__ import annotations

import pytest

from engine import mic


# ----------------------------------------------------------- truth table

@pytest.mark.parametrize(
    "start,stop,expected",
    [
        (132000000000000000, 0, True),       # capturing now
        (132000000000000000, 132000000001, False),  # started then stopped
        (0, 0, False),                       # never captured
        (None, None, False),                 # no values present
        (132000000000000000, None, True),    # start, stop missing -> active
    ],
)
def test_mic_active_truth_table(start, stop, expected):
    assert mic._mic_active(start, stop) is expected


# ----------------------------------------------------------- fake registry

class FakeKey:
    def __init__(self, subkeys: dict, values: dict | None = None):
        self.subkeys = subkeys  # name -> FakeKey
        self.values = values or {}  # value name -> data

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeWinreg:
    HKEY_CURRENT_USER = "HKCU"

    def __init__(self, root: FakeKey):
        self._root = root

    def OpenKey(self, _root, path):
        # path is relative to the consent-store base; walk by backslash
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
    """microphone\\{TeamsActive, SlackIdle, NonPackaged\\{Zoom, OldApp}}"""
    teams = FakeKey({}, {"LastUsedTimeStart": 132_000, "LastUsedTimeStop": 0})
    slack = FakeKey({}, {"LastUsedTimeStart": 130_000, "LastUsedTimeStop": 131_000})
    zoom = FakeKey({}, {"LastUsedTimeStart": 132_500, "LastUsedTimeStop": 0})
    oldapp = FakeKey({}, {"LastUsedTimeStart": 100, "LastUsedTimeStop": 200})
    nonpackaged = FakeKey({"Zoom.exe": zoom, "OldApp.exe": oldapp})
    microphone = FakeKey(
        {
            "MSTeams_xyz": teams,
            "Slack_abc": slack,
            "NonPackaged": nonpackaged,
        }
    )
    # mirror the base path so OpenKey(base) resolves
    root = FakeKey({})
    node = root
    for part in mic._MIC_BASE.split("\\"):
        child = FakeKey({})
        node.subkeys[part] = child
        node = child
    # attach microphone subtree at the leaf
    node.subkeys.update(microphone.subkeys)
    return root


def test_mic_capturers_collects_packaged_and_nonpackaged(monkeypatch):
    fake = FakeWinreg(_build_tree())
    monkeypatch.setattr(mic, "winreg", fake)
    monkeypatch.setattr(mic, "_IS_WINDOWS", True)

    caps = set(mic.mic_capturers())
    assert "MSTeams_xyz" in caps      # packaged, active
    assert "Zoom.exe" in caps          # NonPackaged, active
    assert "Slack_abc" not in caps     # stopped
    assert "OldApp.exe" not in caps    # stopped
    assert mic.mic_in_use() is True


def test_mic_in_use_false_when_no_base_key(monkeypatch):
    empty = FakeWinreg(FakeKey({}))
    monkeypatch.setattr(mic, "winreg", empty)
    monkeypatch.setattr(mic, "_IS_WINDOWS", True)
    assert mic.mic_capturers() == []
    assert mic.mic_in_use() is False

"""Shared test fixtures.

A lightweight stand-in for the live engine State — the resolver only
duck-types ``paused``, ``device_connected``, ``in_call``, and
``manual_override``, so we don't need the real threaded State here.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from engine.config import Config, Routine, Settings


@dataclass
class FakeState:
    paused: bool = False
    device_connected: bool = True
    in_call: bool = False
    manual_override: dict | None = None


@pytest.fixture
def state():
    return FakeState()


@pytest.fixture
def config():
    """Config with no routines and the default settings."""
    return Config(routines=[], settings=Settings())


def routine(**kw) -> Routine:
    base = dict(
        id="r",
        name="R",
        enabled=True,
        days=[0, 1, 2, 3, 4, 5, 6],
        start="09:00",
        end="17:00",
        color="available",
    )
    base.update(kw)
    return Routine(**base)

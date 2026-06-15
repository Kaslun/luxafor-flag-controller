"""Palette: display hex (UI) vs LED-tuned device RGB (physical flag)."""

from __future__ import annotations

from engine.palette import SLOTS, rgb_of


def test_seed_display_hex_is_design_hex():
    # the seed slots carry the designer's display hex (served via the editable
    # palette's default; see tests/test_palette_config.py for the live path)
    assert SLOTS["available"].hex == "#2FCB6F"
    assert SLOTS["away"].hex == "#FFC93D"


def test_rgb_of_returns_led_tuned_values():
    # the flag gets saturated values with the muddying blue channel cut,
    # so green doesn't read as turquoise and yellow isn't washed out
    assert rgb_of("available") == (0, 230, 40)
    assert rgb_of("away") == (255, 190, 0)


def test_led_green_has_low_blue():
    # regression: design green carried blue=111 -> turquoise on the LED
    _r, _g, b = rgb_of("available")
    assert b <= 60


def test_unknown_slot_is_black():
    assert rgb_of("nope") == (0, 0, 0)


def test_off_slot_is_black_everywhere():
    assert rgb_of("off") == (0, 0, 0)
    assert SLOTS["off"].hex == "off"

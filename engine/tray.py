"""System-tray icon and menu (pystray + Pillow).

Mirrors the Beacon design's tray surface: a status header (color orb +
name + reason), a Pause/Resume toggle, an Override section listing every
selectable slot (with a check on the active one) plus Clear override, and
Open Beacon / Quit.

The icon image is rendered at runtime from the current slot color with
small state overlays (paused bars, disconnected slash, override cursor,
update dot), refreshed by a background updater thread. The tray runs on
its own daemon thread; all mutations go through the engine's thread-safe
command methods.
"""

from __future__ import annotations

import threading
import time
import webbrowser

import pystray
from PIL import Image, ImageDraw
from pystray import Menu, MenuItem

from engine.logging_setup import get_logger
from engine.palette import SELECTABLE, name_of, rgb_of

log = get_logger()

_DEFAULT_OVERRIDE_MINUTES = 30


def _rounded(draw: ImageDraw.ImageDraw, box, radius, fill):
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def render_icon(state_snapshot: dict, size: int = 64) -> Image.Image:
    """Compose the tray icon for the current state."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    kind = state_snapshot.get("kind", "off")
    slot = state_snapshot.get("color", "off")
    paused = state_snapshot.get("paused", False)
    disconnected = not state_snapshot.get("device_connected", True)
    has_override = state_snapshot.get("manual_override") is not None
    has_update = state_snapshot.get("update_available") is not None

    s = size / 64.0
    base_box = (8 * s, 10 * s, 56 * s, 44 * s)

    if paused or kind == "off":
        fill = (58, 58, 66, 255)
    elif disconnected:
        fill = (90, 90, 100, 255)
    else:
        r, g, b = rgb_of(slot)
        fill = (r, g, b, 255)
    _rounded(d, base_box, radius=int(8 * s), fill=fill)

    # flag stand
    _rounded(d, (28 * s, 44 * s, 36 * s, 54 * s), int(2 * s), (44, 44, 52, 255))
    _rounded(d, (20 * s, 54 * s, 44 * s, 58 * s), int(2 * s), (44, 44, 52, 255))

    if paused:
        white = (255, 255, 255, 255)
        _rounded(d, (22 * s, 18 * s, 28 * s, 36 * s), int(2 * s), white)
        _rounded(d, (36 * s, 18 * s, 42 * s, 36 * s), int(2 * s), white)
    if disconnected:
        d.line(
            [(12 * s, 14 * s), (52 * s, 40 * s)],
            fill=(255, 255, 255, 255),
            width=int(4 * s),
        )
    if has_override and not paused and not disconnected:
        cx, cy = 46 * s, 24 * s
        d.ellipse(
            [cx - 9 * s, cy - 9 * s, cx + 9 * s, cy + 9 * s], fill=(13, 13, 16, 255)
        )
        d.polygon(
            [
                (cx - 3 * s, cy - 4 * s),
                (cx + 4 * s, cy + 3 * s),
                (cx, cy + 3.5 * s),
                (cx + 2 * s, cy + 7 * s),
                (cx - 4 * s, cy + 5 * s),
            ],
            fill=(255, 255, 255, 255),
        )
    if has_update:
        cx, cy = 52 * s, 14 * s
        d.ellipse(
            [cx - 7 * s, cy - 7 * s, cx + 7 * s, cy + 7 * s],
            fill=(76, 125, 255, 255),
            outline=(13, 13, 16, 255),
            width=int(2 * s),
        )
    return img


class TrayController:
    def __init__(self, engine) -> None:
        self.engine = engine
        self.icon = pystray.Icon("beacon", title="Beacon")
        self.icon.menu = self._build_menu()
        self._updater: threading.Thread | None = None
        self._running = False

    # -------------------------------------------------- menu

    def _status_text(self, _item=None) -> str:
        snap = self.engine.state.snapshot()
        if snap["paused"]:
            return "Paused"
        if not snap["device_connected"]:
            return "Disconnected"
        return name_of(snap["color"])

    def _is_paused(self) -> bool:
        return self.engine.state.snapshot()["paused"]

    def _has_override(self, _item=None) -> bool:
        return self.engine.state.snapshot()["manual_override"] is not None

    def _active_override_slot(self) -> str | None:
        ov = self.engine.state.snapshot()["manual_override"]
        return ov["color"] if ov else None

    def _override_items(self):
        def make(slot):
            return MenuItem(
                name_of(slot),
                lambda icon, item: self.engine.set_override(
                    slot, _DEFAULT_OVERRIDE_MINUTES
                ),
                checked=lambda item, s=slot: self._active_override_slot() == s,
                radio=True,
            )

        return [make(s) for s in SELECTABLE]

    def _build_menu(self) -> Menu:
        return Menu(
            MenuItem(self._status_text, None, enabled=False),
            Menu.SEPARATOR,
            MenuItem(
                lambda item: "Resume Beacon" if self._is_paused() else "Pause Beacon",
                self._toggle_pause,
            ),
            Menu.SEPARATOR,
            MenuItem("Override", Menu(*self._override_items())),
            MenuItem(
                "Clear override",
                lambda icon, item: self.engine.clear_override(),
                visible=self._has_override,
            ),
            Menu.SEPARATOR,
            MenuItem("Open Beacon…", self._open),
            MenuItem("Quit", self._quit),
        )

    # -------------------------------------------------- actions

    def _toggle_pause(self, icon, item):
        self.engine.set_paused(not self._is_paused())

    def _open(self, icon, item):
        port = self.engine.state.port or 54741
        webbrowser.open(f"http://127.0.0.1:{port}/")

    def _quit(self, icon, item):
        self._running = False
        self.engine.stop()
        icon.stop()

    # -------------------------------------------------- lifecycle

    def _refresh_loop(self):
        while self._running:
            try:
                snap = self.engine.state.snapshot()
                self.icon.icon = render_icon(snap)
                self.icon.title = f"Beacon — {self._status_text()}"
            except Exception as e:  # pragma: no cover - defensive
                log.debug("tray refresh failed: %s", e)
            time.sleep(2)

    def run(self):
        """Blocking — call on a dedicated thread."""
        self._running = True
        self.icon.icon = render_icon(self.engine.state.snapshot())
        self._updater = threading.Thread(target=self._refresh_loop, daemon=True)
        self._updater.start()
        self.icon.run()


def start_tray(engine) -> TrayController:
    """Start the tray on a daemon thread and return the controller."""
    controller = TrayController(engine)
    t = threading.Thread(target=controller.run, daemon=True, name="beacon-tray")
    t.start()
    return controller

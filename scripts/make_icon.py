"""Generate packaging/icon.ico from the Beacon mark.

A rounded square in the brand green with a simple beacon glyph. Produces a
multi-resolution .ico used both as the exe icon and a fallback tray image.
Run from the repo root: ``python scripts/make_icon.py``.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

GREEN = (47, 203, 111, 255)
INK = (13, 13, 16, 255)


def draw_base(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 64.0
    d.rounded_rectangle((4 * s, 4 * s, 60 * s, 60 * s), radius=int(14 * s), fill=GREEN)
    # beacon glyph: a small tower / flare
    cx = 32 * s
    d.line([(cx, 18 * s), (cx, 26 * s)], fill=INK, width=int(3 * s))
    d.polygon(
        [(cx - 9 * s, 48 * s), (cx, 28 * s), (cx + 9 * s, 48 * s)],
        outline=INK,
    )
    d.line([(22 * s, 48 * s), (42 * s, 48 * s)], fill=INK, width=int(3 * s))
    return img


def main() -> None:
    out = Path(__file__).resolve().parent.parent / "packaging" / "icon.ico"
    out.parent.mkdir(parents=True, exist_ok=True)
    sizes = [16, 24, 32, 48, 64, 128, 256]
    base = draw_base(256)
    images = [base.resize((sz, sz), Image.LANCZOS) for sz in sizes]
    images[0].save(out, format="ICO", sizes=[(sz, sz) for sz in sizes])
    print(f"wrote {out}")


if __name__ == "__main__":
    main()

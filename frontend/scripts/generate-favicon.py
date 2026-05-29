"""Generate frontend/public/favicon.ico from the CapCore icon (24px, Pillow)."""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_ICO = ROOT / "public" / "favicon.ico"

GOLD = (201, 168, 76, 255)
GOLD_FAINT = (201, 168, 76, 102)


def _draw_icon(size: int):
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 60.0
    cx = cy = 30.0 * s
    lw = max(1, round(1.5 * s))

    # Outer dashed ring (approximation)
    r_outer = 18 * s
    for i in range(0, 360, 14):
        d.arc(
            [cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer],
            start=i,
            end=i + 7,
            fill=GOLD_FAINT,
            width=max(1, round(s)),
        )

    r_mid = 11 * s
    d.ellipse(
        [cx - r_mid, cy - r_mid, cx + r_mid, cy + r_mid],
        outline=GOLD,
        width=lw,
    )

    r_core = 4 * s
    d.ellipse([cx - r_core, cy - r_core, cx + r_core, cy + r_core], fill=GOLD)

    def line(x1: float, y1: float, x2: float, y2: float) -> None:
        d.line([(x1 * s, y1 * s), (x2 * s, y2 * s)], fill=GOLD, width=lw)

    line(30, 12, 30, 19)
    line(30, 41, 30, 48)
    line(12, 30, 19, 30)
    line(41, 30, 48, 30)

    # Arc accents
    d.arc(
        [13 * s, 13 * s, 47 * s, 47 * s],
        start=200,
        end=260,
        fill=GOLD,
        width=max(2, round(2 * s)),
    )
    d.arc(
        [13 * s, 13 * s, 47 * s, 47 * s],
        start=20,
        end=80,
        fill=GOLD,
        width=max(2, round(2 * s)),
    )

    return img


def main() -> int:
    try:
        from PIL import Image
    except ImportError:
        print("Install: pip install pillow", file=sys.stderr)
        return 1

    icon = _draw_icon(24)
    icon.save(OUT_ICO, format="ICO", sizes=[(24, 24)])
    print(f"Wrote {OUT_ICO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

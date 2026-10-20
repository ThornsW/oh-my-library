"""Tiny color helpers for QSS-friendly fragments.

Qt's QSS hex parser treats 8-digit ``#RRGGBBAA`` as ``#AARRGGBB`` — i.e.
the *first* two hex digits are the alpha channel, not the last two. This
trips up anyone reaching for the CSS-standard ``#RRGGBBAA``: a tag like
``#7AA2F71F`` (intended: light blue at 12% opacity) is parsed as alpha=0x7A,
R=0xA2, G=0xF7, B=0x1F — a semi-transparent lime green.

Use :func:`hex_to_rgba` to build a Qt-friendly ``rgba(r, g, b, a)`` literal,
and :func:`darken` to derive a higher-contrast text colour from a tag color.
"""

from __future__ import annotations


def _split_hex(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def hex_to_rgba(hex_color: str, alpha: float = 1.0) -> str:
    """``"#7AA2F7", 0.18 -> "rgba(122, 162, 247, 0.18)"``."""
    r, g, b = _split_hex(hex_color)
    return f"rgba({r}, {g}, {b}, {alpha})"


def darken(hex_color: str, factor: float = 0.4) -> str:
    """Mix toward black by ``factor`` (0-1). Used to derive readable chip
    text colours from a (often light) tag background."""
    r, g, b = _split_hex(hex_color)
    r = max(0, int(r * (1 - factor)))
    g = max(0, int(g * (1 - factor)))
    b = max(0, int(b * (1 - factor)))
    return f"#{r:02X}{g:02X}{b:02X}"

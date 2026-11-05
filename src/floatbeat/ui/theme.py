"""Colours and small colour helpers. One palette, no magic numbers in painters."""

from __future__ import annotations

from PySide6.QtGui import QColor

# Body
INK_TOP = QColor("#2a2f42")
INK_BOTTOM = QColor("#14161f")
INK_EDGE = QColor("#3a4055")
VISOR_BG = QColor(7, 9, 14, 250)
CONSOLE_BG = QColor(12, 14, 22, 242)

# Neon
CYAN = QColor("#00f0d0")
CYAN_DIM = QColor(0, 240, 208, 150)
MAGENTA = QColor("#ff3ea5")
WHITE = QColor("#eafffb")
BLACK = QColor(0, 0, 0)

# Low band to high band, kept saturated in the middle (a plain cyan→magenta
# interpolation goes grey around the centre).
BAR_PALETTE = (CYAN, QColor("#00c8f0"), QColor("#6e7bff"), QColor("#c05cff"), MAGENTA)


def lerp(a: QColor, b: QColor, t: float) -> QColor:
    """Linear interpolation between two colours, preserving alpha."""
    t = max(0.0, min(1.0, t))
    return QColor(
        round(a.red() + (b.red() - a.red()) * t),
        round(a.green() + (b.green() - a.green()) * t),
        round(a.blue() + (b.blue() - a.blue()) * t),
        round(a.alpha() + (b.alpha() - a.alpha()) * t),
    )


def band_color(index: int, count: int) -> QColor:
    """Cyan through violet to magenta, staying saturated in the middle."""
    if count <= 1:
        return CYAN
    pos = (index / (count - 1)) * (len(BAR_PALETTE) - 1)
    left = min(int(pos), len(BAR_PALETTE) - 2)
    return lerp(BAR_PALETTE[left], BAR_PALETTE[left + 1], pos - left)


def with_alpha(color: QColor, alpha: int) -> QColor:
    return QColor(color.red(), color.green(), color.blue(), alpha)

"""Colours for the avatar and the future popover."""

from __future__ import annotations

from PySide6.QtGui import QColor

# Blob avatar
SHELL = QColor("#d9d9d9")
SHELL_EDGE = QColor(0, 0, 0, 38)
DESK_FILL = QColor("#0b0b0c")
DESK_EDGE = QColor("#4a4a4a")
ROPE = QColor(140, 140, 140, 210)
WHITE = QColor("#eafffb")

# The eyes carry the only colour.
EYE_ACCENT = QColor("#25f4d2")
EYE_ACCENT_DEEP = QColor("#00a892")


def lerp(a: QColor, b: QColor, t: float) -> QColor:
    """Linear interpolation between two colours, preserving alpha."""
    t = max(0.0, min(1.0, t))
    return QColor(
        round(a.red() + (b.red() - a.red()) * t),
        round(a.green() + (b.green() - a.green()) * t),
        round(a.blue() + (b.blue() - a.blue()) * t),
        round(a.alpha() + (b.alpha() - a.alpha()) * t),
    )


def with_alpha(color: QColor, alpha: int) -> QColor:
    return QColor(color.red(), color.green(), color.blue(), alpha)

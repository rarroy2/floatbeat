"""Window placement and display-server quirks.

Wayland deliberately does not let a client position a top-level window or decide
its stacking order. XWayland still does, so we default to it when both backends
are available. See docs/DECISIONS.md (ADR-003).

Placement is anchored to the *available* geometry, which the desktop already
shrinks to exclude panels and docks. That is how Floatbeat ends up under the top
bar (next to the clock on GNOME, or wherever the user moved their panel) without
needing a compositor-specific plugin.
"""

from __future__ import annotations

import os

from PySide6.QtCore import QPoint, QRect, QSize
from PySide6.QtGui import QGuiApplication, QScreen

DEFAULT_ANCHOR = "top-right"
DEFAULT_MARGIN = 24
ANCHORS = ("top-right", "top-left", "bottom-right", "bottom-left")

ANCHOR_LABELS = {
    "top-right": "Arriba derecha",
    "top-left": "Arriba izquierda",
    "bottom-right": "Abajo derecha",
    "bottom-left": "Abajo izquierda",
}


def prefer_xwayland() -> str:
    """Pick the Qt platform plugin. Must run before QApplication is created.

    An explicit ``QT_QPA_PLATFORM`` always wins, and
    ``FLOATBEAT_NATIVE_WAYLAND=1`` opts back into a native Wayland session.
    Returns the plugin name that will be used (or an empty string if Qt decides).
    """
    explicit = os.environ.get("QT_QPA_PLATFORM")
    if explicit:
        return explicit
    if not os.environ.get("WAYLAND_DISPLAY"):
        return os.environ.get("DISPLAY") and "xcb" or ""
    if os.environ.get("FLOATBEAT_NATIVE_WAYLAND") == "1":
        return "wayland"
    if os.environ.get("DISPLAY"):
        os.environ["QT_QPA_PLATFORM"] = "xcb"
        return "xcb"
    return "wayland"


def anchor_position(
    area: QRect,
    size: QSize,
    anchor: str = DEFAULT_ANCHOR,
    margin: int = DEFAULT_MARGIN,
) -> QPoint:
    """Top-left corner for a window of ``size`` inside ``area`` (work area)."""
    if anchor not in ANCHORS:
        raise ValueError(f"unknown anchor: {anchor!r}")
    x = area.x() + area.width() - size.width() - margin if anchor.endswith("right") else area.x() + margin
    y = area.y() + margin if anchor.startswith("top") else area.y() + area.height() - size.height() - margin
    return QPoint(x, y)


def position_for_anchor(
    anchor: str = DEFAULT_ANCHOR,
    size: QSize | None = None,
    margin: int = DEFAULT_MARGIN,
    screen: QScreen | None = None,
) -> QPoint:
    """Same as :func:`anchor_position`, resolved against a real screen."""
    target = screen or QGuiApplication.primaryScreen()
    if target is None:
        return QPoint(margin, margin)
    return anchor_position(target.availableGeometry(), size or QSize(220, 220), anchor, margin)


def default_position(size: QSize) -> QPoint:
    """First-run position: top-right of the work area, under the panel."""
    return position_for_anchor(DEFAULT_ANCHOR, size)


def is_on_some_screen(pos: QPoint, size: QSize) -> bool:
    """True when at least part of a window at ``pos`` is reachable."""
    window_rect = QRect(pos, size)
    for screen in QGuiApplication.screens():
        if screen.availableGeometry().intersects(window_rect):
            return True
    return False


def restore_window_position(
    saved: QPoint | None,
    size: QSize,
    anchor: str = DEFAULT_ANCHOR,
    margin: int = DEFAULT_MARGIN,
) -> QPoint:
    """Use the saved position if it is still visible, else the anchor."""
    if isinstance(saved, QPoint) and is_on_some_screen(saved, size):
        return saved
    return position_for_anchor(anchor, size, margin)

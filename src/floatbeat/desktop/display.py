"""Window placement and display-server quirks.

Wayland deliberately does not let a client position a top-level window or decide
its stacking order. XWayland still does, so we default to it when both backends
are available. See docs/DECISIONS.md (ADR-003).
"""

from __future__ import annotations

import os

from PySide6.QtCore import QPoint
from PySide6.QtGui import QGuiApplication


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


def default_position(size, margin: int = 36) -> QPoint:
    """Bottom-right corner of the primary screen, inset by ``margin``."""
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        return QPoint(margin, margin)
    area = screen.availableGeometry()
    return QPoint(
        area.right() - size.width() - margin,
        area.bottom() - size.height() - margin,
    )


def is_on_some_screen(pos: QPoint, size) -> bool:
    """True when at least part of a window at ``pos`` is reachable."""
    window_rect = (pos.x(), pos.y(), size.width(), size.height())
    for screen in QGuiApplication.screens():
        area = screen.availableGeometry()
        if (
            window_rect[0] + window_rect[2] > area.left()
            and window_rect[0] < area.right()
            and window_rect[1] + window_rect[3] > area.top()
            and window_rect[1] < area.bottom()
        ):
            return True
    return False


def restore_window_position(saved: QPoint | None, size) -> QPoint:
    """Use the saved position if it is still visible, else a safe default."""
    if isinstance(saved, QPoint) and is_on_some_screen(saved, size):
        return saved
    return default_position(size)

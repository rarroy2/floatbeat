"""Frameless floating window: painting, dragging, menu, position memory."""

from __future__ import annotations

import time
from collections.abc import Sequence

from PySide6.QtCore import QPoint, QSettings, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QActionGroup, QMouseEvent, QPainter
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from ..desktop.display import (
    ANCHOR_LABELS,
    ANCHORS,
    DEFAULT_ANCHOR,
    DEFAULT_MARGIN,
    position_for_anchor,
    restore_window_position,
)
from .avatar import FRAME_DIRTY, LED_DIRTY, VISOR_DIRTY, WIDGET_SIZE, AvatarRenderer

MENU_STYLE = """
QMenu {
    background-color: #14161f;
    color: #eafffb;
    border: 1px solid #2a2f42;
    padding: 6px;
}
QMenu::item { padding: 6px 22px 6px 14px; border-radius: 4px; }
QMenu::item:selected { background-color: #00f0d0; color: #0b0d12; }
QMenu::separator { height: 1px; background: #2a2f42; margin: 5px 8px; }
"""


class FloatbeatWidget(QWidget):
    pause_toggled = Signal(bool)
    quit_requested = Signal()

    def __init__(self, settings: QSettings) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setWindowTitle("Floatbeat")
        self.setFixedSize(WIDGET_SIZE)

        self._settings = settings
        # Older builds had no anchor setting and stored a bottom-right position.
        # Treat that as a migration: honour the new anchor once, then keep the
        # user's manual position.
        stored_anchor = settings.value("window/anchor")
        self._anchor = str(stored_anchor) if stored_anchor in ANCHORS else DEFAULT_ANCHOR
        self._margin = int(settings.value("window/margin", DEFAULT_MARGIN))
        self._anchor_is_new = stored_anchor is None
        self._renderer = AvatarRenderer()
        self.paints = 0
        self.paint_seconds = 0.0
        self._frame = 0
        self._press_global = QPoint()
        self._press_offset = QPoint()
        self._dragging = False
        self._manual_move = False
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(400)
        self._save_timer.timeout.connect(self._save_position)

        self._menu = QMenu(self)
        self._menu.setStyleSheet(MENU_STYLE)
        self._pause_action = QAction("Pausar animación", self)
        self._pause_action.setCheckable(True)
        self._pause_action.toggled.connect(self.pause_toggled)
        self._menu.addAction(self._pause_action)
        self._menu.addSeparator()

        position_menu = self._menu.addMenu("Posición en pantalla")
        self._anchor_group = QActionGroup(self)
        self._anchor_group.setExclusive(True)
        for anchor in ANCHORS:
            action = QAction(ANCHOR_LABELS[anchor], self)
            action.setCheckable(True)
            action.setChecked(anchor == self._anchor)
            action.triggered.connect(lambda _checked, a=anchor: self.set_anchor(a))
            self._anchor_group.addAction(action)
            position_menu.addAction(action)

        self._menu.addSeparator()
        self._menu.addAction("Salir", self.quit_requested.emit)

    # -- lifecycle ----------------------------------------------------------

    def restore_position(self) -> None:
        if self._anchor_is_new:
            self.move(position_for_anchor(self._anchor, self.size(), self._margin))
            self._settings.setValue("window/anchor", self._anchor)
            self._anchor_is_new = False
            return
        saved = self._settings.value("window/pos")
        if not isinstance(saved, QPoint):
            saved = None
        self.move(restore_window_position(saved, self.size(), self._anchor, self._margin))

    def set_anchor(self, anchor: str) -> None:
        """Snap to a corner of the work area (panel-aware) and remember it."""
        if anchor not in ANCHORS:
            return
        self._anchor = anchor
        self._anchor_is_new = False
        self._settings.setValue("window/anchor", anchor)
        self.move(position_for_anchor(anchor, self.size(), self._margin))
        self._save_position()

    def show_idle(self) -> None:
        """Paint the resting pose once, then stay silent."""
        # now=1.0 keeps the periodic blink from landing on phase 0 (which would
        # leave the eyes closed forever while the clock is stopped).
        self._renderer.set_frame((0.0, 0.0, 0.0, 0.0), 0.0, 0.0, 1.0)
        self.update(FRAME_DIRTY)

    # -- frame feed ---------------------------------------------------------

    def set_frame(self, bands: Sequence[float], level: float, dt: float, now: float) -> None:
        self._renderer.set_frame(bands, level, dt, now)
        self.update(FRAME_DIRTY)
        self._frame += 1
        if self._frame % 3 == 0:
            self.update(LED_DIRTY)

    def blink(self) -> None:
        """One-off reaction that also works while the render timer is stopped."""
        self._renderer.poke()
        self.update(VISOR_DIRTY)
        QTimer.singleShot(170, lambda: self.update(VISOR_DIRTY))
        # Settle the 300 ms bounce even when the render timer is stopped.
        QTimer.singleShot(340, lambda: self.update(VISOR_DIRTY))

    # -- painting -----------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        del event
        started = time.perf_counter()
        self.paints += 1
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self._renderer.paint(painter, self.size())
        painter.end()
        self.paint_seconds += time.perf_counter() - started

    # -- dragging -----------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_global = event.globalPosition().toPoint()
            self._dragging = False
            self._manual_move = False
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self._menu.popup(event.globalPosition().toPoint())
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return super().mouseMoveEvent(event)
        global_pos = event.globalPosition().toPoint()
        if not self._dragging:
            if (global_pos - self._press_global).manhattanLength() < QApplication.startDragDistance():
                return
            self._dragging = True
            self._press_offset = self._press_global - self.frameGeometry().topLeft()
            handle = self.windowHandle()
            moved = handle.startSystemMove() if handle is not None else False
            self._manual_move = not moved
        if self._manual_move:
            self.move(global_pos - self._press_offset)
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            if not self._dragging:
                self.blink()
            self._dragging = False
            self._manual_move = False
            self._save_position()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def moveEvent(self, event) -> None:  # noqa: N802
        super().moveEvent(event)
        self._save_timer.start()

    def closeEvent(self, event) -> None:  # noqa: N802
        self._save_position()
        super().closeEvent(event)

    # -- helpers ------------------------------------------------------------

    def set_paused(self, paused: bool) -> None:
        self._pause_action.blockSignals(True)
        self._pause_action.setChecked(paused)
        self._pause_action.setText("Reanudar animación" if paused else "Pausar animación")
        self._pause_action.blockSignals(False)

    def _save_position(self) -> None:
        self._settings.setValue("window/pos", self.pos())

    def sizeHint(self) -> QSize:  # noqa: N802
        return WIDGET_SIZE

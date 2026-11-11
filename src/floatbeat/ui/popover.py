"""Translucent mixer popover: big avatar, artwork, metadata and controls.

Opened from the panel actor through the engine's D-Bus API. It is a ``Qt.Popup``
so clicking anywhere else closes it, and it paints its own rounded, translucent
surface (no OS chrome).
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, QUrl, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QGuiApplication,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtWidgets import QWidget

from .blob import BlobAvatarRenderer

WIDTH = 430
HEIGHT = 250

ART_RECT = QRectF(24.0, 24.0, 110.0, 110.0)
TEXT_X = 152.0
TEXT_W = 254.0
PROGRESS_RECT = QRectF(TEXT_X, 100.0, TEXT_W, 4.0)
AVATAR_POS = QPointF(24.0, 150.0)
AVATAR_SCALE = 0.9
AVATAR_DIRTY = QRectF(14.0, 140.0, 200.0, 108.0)
CONTROL_Y = 152.0
CONTROLS = {
    "previous": QPointF(250.0, CONTROL_Y),
    "play": QPointF(300.0, CONTROL_Y),
    "next": QPointF(350.0, CONTROL_Y),
}
CONTROL_RADIUS = {"previous": 18.0, "play": 22.0, "next": 18.0}

BG = QColor(13, 15, 20, 238)
BORDER = QColor(255, 255, 255, 30)
TEXT = QColor("#eafffb")
MUTED = QColor("#9aa3a8")
DIM = QColor("#6f777c")
ACCENT = QColor("#25f4d2")
BUTTON = QColor(255, 255, 255, 12)
BUTTON_HOVER = QColor(255, 255, 255, 26)
TRACK_BG = QColor(255, 255, 255, 28)


class Popover(QWidget):
    play_pause = Signal()
    next_track = Signal()
    previous_track = Signal()

    def __init__(self) -> None:
        super().__init__(None, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFixedSize(WIDTH, HEIGHT)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._title = ""
        self._artist = ""
        self._album = ""
        self._art_url = ""
        self._art: QPixmap | None = None
        self._art_cache: dict[str, QPixmap] = {}
        self._position_us = 0
        self._length_us = 0
        self._playing = False
        self._hovered: str | None = None
        self._has_track = False

        self._renderer = BlobAvatarRenderer()
        self._network = QNetworkAccessManager(self)
        self._font_title = QFont()
        self._font_title.setPointSizeF(13.5)
        self._font_title.setWeight(QFont.Weight.DemiBold)
        self._font_body = QFont()
        self._font_body.setPointSizeF(10.5)

    # -- state --------------------------------------------------------------

    def set_track(
        self,
        *,
        title: str,
        artist: str,
        album: str,
        art_url: str,
        position_us: int,
        length_us: int,
        playing: bool,
    ) -> None:
        changed = (
            title != self._title
            or artist != self._artist
            or album != self._album
            or art_url != self._art_url
            or playing != self._playing
        )
        self._title = title
        self._artist = artist
        self._album = album
        self._position_us = position_us
        self._length_us = length_us
        self._playing = playing
        self._has_track = bool(title)
        if art_url != self._art_url:
            self._art_url = art_url
            self._load_art(art_url)
        if changed:
            self.update()

    def set_frame(self, bands, level: float, dt: float, now: float, playing: bool) -> None:
        self._renderer.set_frame(bands, level, dt, now, playing=playing)
        self.update(AVATAR_DIRTY.toRect())

    # -- placement ----------------------------------------------------------

    def show_at(self, center_x: int, top: int) -> None:
        screen = QGuiApplication.screenAt(QPoint(center_x, top)) or QGuiApplication.primaryScreen()
        area = screen.availableGeometry() if screen else self.rect()
        x = max(area.left() + 8, min(center_x - WIDTH // 2, area.right() - WIDTH - 8))
        y = min(top + 8, area.bottom() - HEIGHT - 8)
        self.move(x, max(area.top() + 8, y))
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()

    # -- painting -----------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        surface = QPainterPath()
        surface.addRoundedRect(QRectF(0.5, 0.5, WIDTH - 1, HEIGHT - 1), 22.0, 22.0)
        painter.setBrush(BG)
        painter.setPen(QPen(BORDER, 1.0))
        painter.drawPath(surface)

        self._paint_artwork(painter)
        self._paint_text(painter)
        self._paint_progress(painter)
        self._paint_controls(painter)
        self._paint_avatar(painter)

        painter.end()

    def _paint_artwork(self, painter: QPainter) -> None:
        path = QPainterPath()
        path.addRoundedRect(ART_RECT, 11.0, 11.0)
        painter.save()
        painter.setClipPath(path)
        if self._art is not None and not self._art.isNull():
            scaled = self._art.scaled(
                ART_RECT.size().toSize(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            source = QRectF(
                (scaled.width() - ART_RECT.width()) / 2.0,
                (scaled.height() - ART_RECT.height()) / 2.0,
                ART_RECT.width(),
                ART_RECT.height(),
            )
            painter.drawPixmap(ART_RECT, scaled, source)
        else:
            gradient = QLinearGradient(ART_RECT.topLeft(), ART_RECT.bottomRight())
            gradient.setColorAt(0.0, QColor("#20242e"))
            gradient.setColorAt(1.0, QColor("#12151c"))
            painter.fillRect(ART_RECT, gradient)
            note = QFont()
            note.setPointSizeF(26)
            painter.setFont(note)
            painter.setPen(QColor(255, 255, 255, 45))
            painter.drawText(ART_RECT, Qt.AlignmentFlag.AlignCenter, "\u266a")
        painter.restore()

    def _paint_text(self, painter: QPainter) -> None:
        title = self._title or "Nothing playing"
        painter.setFont(self._font_title)
        painter.setPen(TEXT if self._has_track else MUTED)
        metrics = QFontMetrics(self._font_title)
        painter.drawText(
            QRectF(TEXT_X, 26.0, TEXT_W, 22.0),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            metrics.elidedText(title, Qt.TextElideMode.ElideRight, int(TEXT_W)),
        )

        painter.setFont(self._font_body)
        painter.setPen(MUTED)
        metrics = QFontMetrics(self._font_body)
        artist = metrics.elidedText(
            self._artist or "Start something on Spotify, VLC or a browser",
            Qt.TextElideMode.ElideRight,
            int(TEXT_W),
        )
        painter.drawText(QRectF(TEXT_X, 50.0, TEXT_W, 18.0), Qt.AlignmentFlag.AlignLeft, artist)

        if self._album:
            painter.setPen(DIM)
            painter.drawText(
                QRectF(TEXT_X, 68.0, TEXT_W, 16.0),
                Qt.AlignmentFlag.AlignLeft,
                metrics.elidedText(self._album, Qt.TextElideMode.ElideRight, int(TEXT_W)),
            )

    def _paint_progress(self, painter: QPainter) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(TRACK_BG)
        painter.drawRoundedRect(PROGRESS_RECT, 2.0, 2.0)
        if self._length_us <= 0:
            return
        ratio = max(0.0, min(1.0, self._position_us / self._length_us))
        filled = QRectF(PROGRESS_RECT)
        filled.setWidth(PROGRESS_RECT.width() * ratio)
        painter.setBrush(ACCENT if self._playing else MUTED)
        painter.drawRoundedRect(filled, 2.0, 2.0)

    def _paint_controls(self, painter: QPainter) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        for name, center in CONTROLS.items():
            radius = CONTROL_RADIUS[name]
            hovered = self._hovered == name
            painter.setBrush(BUTTON_HOVER if hovered else BUTTON)
            painter.drawEllipse(center, radius, radius)
            self._paint_symbol(painter, name, center, radius, hovered)

    def _paint_symbol(
        self, painter: QPainter, name: str, center: QPointF, radius: float, hovered: bool
    ) -> None:
        color = ACCENT if hovered else TEXT
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        s = radius * 0.52
        if name == "play":
            if self._playing:
                painter.drawRoundedRect(
                    QRectF(center.x() - s * 0.75, center.y() - s, s * 0.55, s * 2.0), 1.0, 1.0
                )
                painter.drawRoundedRect(
                    QRectF(center.x() + s * 0.2, center.y() - s, s * 0.55, s * 2.0), 1.0, 1.0
                )
            else:
                path = QPainterPath()
                path.moveTo(center.x() - s * 0.55, center.y() - s)
                path.lineTo(center.x() + s * 0.95, center.y())
                path.lineTo(center.x() - s * 0.55, center.y() + s)
                path.closeSubpath()
                painter.drawPath(path)
        elif name == "next":
            painter.drawRoundedRect(
                QRectF(center.x() + s * 0.45, center.y() - s, s * 0.35, s * 2.0), 1.0, 1.0
            )
            path = QPainterPath()
            path.moveTo(center.x() - s * 0.75, center.y() - s)
            path.lineTo(center.x() + s * 0.35, center.y())
            path.lineTo(center.x() - s * 0.75, center.y() + s)
            path.closeSubpath()
            painter.drawPath(path)
        else:
            painter.drawRoundedRect(
                QRectF(center.x() - s * 0.8, center.y() - s, s * 0.35, s * 2.0), 1.0, 1.0
            )
            path = QPainterPath()
            path.moveTo(center.x() + s * 0.8, center.y() - s)
            path.lineTo(center.x() - s * 0.3, center.y())
            path.lineTo(center.x() + s * 0.8, center.y() + s)
            path.closeSubpath()
            painter.drawPath(path)

    def _paint_avatar(self, painter: QPainter) -> None:
        painter.save()
        painter.translate(AVATAR_POS)
        painter.scale(AVATAR_SCALE, AVATAR_SCALE)
        self._renderer.paint(painter, self._renderer.size)
        painter.restore()

    # -- interaction --------------------------------------------------------

    def _control_at(self, pos: QPointF) -> str | None:
        for name, center in CONTROLS.items():
            if (pos - center).manhattanLength() <= CONTROL_RADIUS[name] * 1.6:
                return name
        return None

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        hovered = self._control_at(event.position())
        if hovered != self._hovered:
            self._hovered = hovered
            self.update()
        self.setCursor(
            Qt.CursorShape.PointingHandCursor
            if hovered
            else Qt.CursorShape.ArrowCursor
        )

    def leaveEvent(self, event) -> None:  # noqa: N802
        del event
        if self._hovered:
            self._hovered = None
            self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        control = self._control_at(event.position())
        if control == "play":
            self.play_pause.emit()
        elif control == "next":
            self.next_track.emit()
        elif control == "previous":
            self.previous_track.emit()
        event.accept()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    # -- artwork ------------------------------------------------------------

    def _load_art(self, url: str) -> None:
        self._art = self._art_cache.get(url)
        if not url:
            self.update()
            return
        if url.startswith("file://"):
            pixmap = QPixmap(QUrl(url).toLocalFile())
            if not pixmap.isNull():
                self._art_cache[url] = pixmap
                self._art = pixmap
            self.update()
            return
        if not url.startswith(("http://", "https://")):
            return
        request = QNetworkRequest(QUrl(url))
        reply = self._network.get(request)
        reply.finished.connect(lambda r=reply, u=url: self._art_finished(r, u))

    def _art_finished(self, reply, url: str) -> None:
        data = bytes(reply.readAll())
        reply.deleteLater()
        pixmap = QPixmap()
        if not data or not pixmap.loadFromData(data):
            return
        self._art_cache[url] = pixmap
        if url == self._art_url:
            self._art = pixmap
            self.update()

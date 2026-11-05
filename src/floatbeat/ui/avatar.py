"""Procedural DJ avatar.

Everything is drawn with QPainter: no sprites, no Lottie, no assets to lose.
The static body is cached in a QPixmap; only the visor, the bars and the LED are
repainted, which is what keeps the CPU cost inside the budget.
"""

from __future__ import annotations

import math
import time
from collections.abc import Sequence

from PySide6.QtCore import QPointF, QRect, QRectF, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)

from .theme import (
    CONSOLE_BG,
    CYAN,
    INK_BOTTOM,
    INK_TOP,
    MAGENTA,
    VISOR_BG,
    WHITE,
    band_color,
    lerp,
    with_alpha,
)

WIDGET_SIZE = QSize(220, 220)
BAND_COUNT = 4
BAR_COUNT = 5

# Regions that change every frame. Kept generously padded so the tilt, the bob
# and the glow never leave a stale pixel behind.
VISOR_W = 112.0
VISOR_H = 44.0
VISOR_PAD = 12.0  # room for the outer glow inside the cached plate

VISOR_DIRTY = QRect(28, 58, 164, 98)
BARS_DIRTY = QRect(30, 168, 160, 50)
LED_DIRTY = QRect(92, 0, 36, 36)
ALL_DIRTY = (VISOR_DIRTY, BARS_DIRTY, LED_DIRTY)
# One damage rect per frame: three separate updates cost three paint events and
# compositing round-trips, which measured slower than a single slightly larger
# region (docs/BENCHMARKS.md).
FRAME_DIRTY = QRect(28, 54, 164, 164)

class AvatarRenderer:
    """Draws one frame of the avatar. Owns no Qt objects beyond a pixmap cache."""

    def __init__(self) -> None:
        self._body: QImage | None = None
        self._cache_key: tuple[int, int, float] | None = None
        self._plate: QImage | None = None
        self._plate_key: float | None = None
        self._bands: tuple[float, ...] = (0.0,) * BAND_COUNT
        self._level = 0.0
        self._bob = 0.0
        self._tilt = 0.0
        self._now = 0.0
        self._poke_at = -10.0
        self._blink_at = -10.0

    # -- public API ---------------------------------------------------------

    def set_frame(
        self,
        bands: Sequence[float],
        level: float,
        dt: float,
        now: float,
    ) -> None:
        del dt  # reserved for future physics; frame-rate independence lives in app
        self._bands = tuple(bands)
        self._level = _clamp(level)
        self._now = now
        self._bob = math.sin(now * 2.2) * 2.0 * self._level
        # "scratching": the visor leans toward whichever end of the spectrum wins
        self._tilt = (self._bands[3] - self._bands[0]) * 2.6

    def poke(self) -> None:
        """React to a click: squint and bounce once."""
        self._poke_at = time.monotonic()
        self._blink_at = self._poke_at

    def paint(self, painter: QPainter, size: QSize) -> None:
        dpr = painter.device().devicePixelRatioF()
        key = (size.width(), size.height(), dpr)
        if self._body is None or self._cache_key != key:
            self._body = self._build_body(size, dpr)
            self._cache_key = key
        painter.drawImage(0, 0, self._body)
        self._paint_visor(painter)
        self._paint_bars(painter)
        self._paint_led(painter)

    # -- animated pieces ----------------------------------------------------

    def _paint_visor(self, painter: QPainter) -> None:
        poke = self._poke()
        painter.save()
        painter.translate(110.0, 106.0 + self._bob - poke * 4.0)

        dpr = painter.device().devicePixelRatioF()
        if self._plate is None or self._plate_key != dpr:
            self._plate = self._build_visor(dpr)
            self._plate_key = dpr
        painter.drawImage(
            QPointF(-VISOR_W / 2.0 - VISOR_PAD, -VISOR_H / 2.0 - VISOR_PAD),
            self._plate,
        )

        eye_height = 10.0 + 21.0 * self._level
        if self._blinking():
            eye_height = 2.4
        eye_height *= 1.0 - 0.35 * poke
        radius = min(9.0, eye_height / 2.0)

        # Spectral balance moves the gaze left (bass) or right (treble) instead
        # of rotating the whole plate, which measured 0.65 ms/frame for a 2.6°
        # tilt (docs/BENCHMARKS.md).
        gaze = _clamp(self._tilt * 1.4, -4.0, 4.0)
        eye_color = lerp(CYAN, WHITE, 0.55)
        for ex in (-24.0, 24.0):
            eye = QRectF(ex + gaze - 12.0, -eye_height / 2.0, 24.0, eye_height)
            painter.setBrush(eye_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(eye, radius, radius)
            if eye_height > 8.0:
                painter.setBrush(QColor(255, 255, 255, 210))
                painter.drawEllipse(QPointF(ex + 5.0, -eye_height / 2.0 + 5.0), 1.7, 1.7)

        painter.restore()

    def _paint_bars(self, painter: QPainter) -> None:
        values = self._bar_values()
        painter.setPen(Qt.PenStyle.NoPen)
        for i, value in enumerate(values):
            height = 4.0 + 26.0 * value
            x = 54.0 + i * 24.0
            color = band_color(i, BAR_COUNT)
            painter.setBrush(with_alpha(color, 22))
            painter.drawRoundedRect(QRectF(x, 178.0, 17.0, 30.0), 4.0, 4.0)
            rect = QRectF(x, 208.0 - height, 17.0, height)
            painter.setBrush(with_alpha(color, 235))
            painter.drawRoundedRect(rect, 4.0, 4.0)
            if height > 7.0:
                painter.setBrush(with_alpha(WHITE, 195))
                painter.drawRoundedRect(QRectF(rect.x() + 3.0, rect.y(), 11.0, 2.0), 1.0, 1.0)

    def _paint_led(self, painter: QPainter) -> None:
        radius = 3.0 + 2.4 * self._level
        color = lerp(CYAN, MAGENTA, min(1.0, self._level * 1.2))
        center = QPointF(110.0, 16.5)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(with_alpha(color, 55))
        painter.drawEllipse(center, radius + 4.0, radius + 4.0)
        painter.setBrush(color)
        painter.drawEllipse(center, radius, radius)
        painter.setBrush(QColor(255, 255, 255, 200))
        painter.drawEllipse(QPointF(109.2, 15.7), radius * 0.35, radius * 0.35)

    def _bar_values(self) -> tuple[float, ...]:
        if len(self._bands) < 2:
            return (self._level,) * BAR_COUNT
        b = self._bands
        return (
            b[0],
            (b[0] + b[1]) * 0.5,
            (b[1] + b[2]) * 0.5,
            (b[2] + b[3]) * 0.5,
            b[3],
        )

    def _blinking(self) -> bool:
        if time.monotonic() - self._blink_at < 0.13:
            return True
        return (self._now % 5.4) < 0.10

    def _poke(self) -> float:
        elapsed = time.monotonic() - self._poke_at
        return max(0.0, 1.0 - elapsed / 0.30)

    # -- cached body --------------------------------------------------------

    def _build_visor(self, dpr: float) -> QImage:
        width = round((VISOR_W + VISOR_PAD * 2) * dpr)
        height = round((VISOR_H + VISOR_PAD * 2) * dpr)
        image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        image.setDevicePixelRatio(dpr)
        image.fill(Qt.GlobalColor.transparent)

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.translate(VISOR_PAD, VISOR_PAD)

        plate = QPainterPath()
        plate.addRoundedRect(QRectF(0.0, 0.0, VISOR_W, VISOR_H), 19.0, 19.0)
        painter.setBrush(VISOR_BG)
        painter.setPen(QPen(with_alpha(CYAN, 55), 7.0))
        painter.drawPath(plate)
        painter.setPen(QPen(with_alpha(CYAN, 190), 1.5))
        painter.drawPath(plate)
        painter.end()
        return image

    def _build_body(self, size: QSize, dpr: float) -> QImage:
        # QImage, not QPixmap: the widget paints through the raster engine, and
        # blitting an X11 pixmap into it forces a round-trip per frame.
        image = QImage(
            round(size.width() * dpr),
            round(size.height() * dpr),
            QImage.Format.Format_ARGB32_Premultiplied,
        )
        image.setDevicePixelRatio(dpr)
        image.fill(Qt.GlobalColor.transparent)

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Contact shadow.
        shadow = QRadialGradient(QPointF(110.0, 168.0), 92.0)
        shadow.setColorAt(0.0, QColor(0, 0, 0, 125))
        shadow.setColorAt(0.7, QColor(0, 0, 0, 45))
        shadow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(shadow)
        painter.drawEllipse(QRectF(18.0, 150.0, 184.0, 40.0))

        # Headphone band: the silhouette cue that says "DJ", not "chat bubble".
        band = QPainterPath()
        band.moveTo(22.0, 102.0)
        band.cubicTo(22.0, -12.0, 198.0, -12.0, 198.0, 102.0)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(INK_TOP, 9.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawPath(band)
        painter.setPen(QPen(QColor("#363d55"), 5.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawPath(band)

        # Ear cups.
        for x in (12.0, 190.0):
            cup = QRectF(x, 84.0, 18.0, 40.0)
            painter.setBrush(INK_TOP)
            painter.setPen(QPen(with_alpha(CYAN, 85), 1.2))
            painter.drawRoundedRect(cup, 9.0, 9.0)
            painter.setPen(QPen(QColor(255, 255, 255, 22), 1.0))
            painter.drawRoundedRect(cup.adjusted(4.0, 7.0, -4.0, -7.0), 5.0, 5.0)

        # Cube body.
        cube = QRectF(35.0, 44.0, 150.0, 124.0)
        body = QPainterPath()
        body.addRoundedRect(cube, 28.0, 28.0)

        fill = QLinearGradient(cube.topLeft(), cube.bottomLeft())
        fill.setColorAt(0.0, INK_TOP)
        fill.setColorAt(1.0, INK_BOTTOM)
        painter.setBrush(fill)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(body)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(with_alpha(CYAN, 40), 6.0))
        painter.drawPath(body)
        painter.setPen(QPen(with_alpha(CYAN, 155), 1.6))
        painter.drawPath(body)

        bevel = QPainterPath()
        bevel.addRoundedRect(cube.adjusted(5.0, 5.0, -5.0, -5.0), 23.0, 23.0)
        painter.setPen(QPen(QColor(255, 255, 255, 26), 1.0))
        painter.drawPath(bevel)

        # Speaker grille under the visor: fills the "chin" without adding noise.
        painter.setPen(QPen(with_alpha(CYAN, 26), 1.2))
        for offset in (139.0, 146.0):
            painter.drawLine(QPointF(84.0, offset), QPointF(136.0, offset))

        # Console plate for the bars.
        console = QRectF(38.0, 176.0, 144.0, 36.0)
        plate = QPainterPath()
        plate.addRoundedRect(console, 14.0, 14.0)
        painter.setBrush(CONSOLE_BG)
        painter.setPen(QPen(QColor(255, 255, 255, 20), 1.0))
        painter.drawPath(plate)

        painter.setPen(QPen(QColor(255, 255, 255, 12), 1.0))
        painter.drawLine(QPointF(50.0, 180.0), QPointF(170.0, 180.0))

        painter.end()
        return image


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))

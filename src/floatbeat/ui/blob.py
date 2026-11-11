"""The hanging avatar: a light rectangle, coloured eyes, arms and a mixer desk.

The whole rig hangs from two ropes that start at the very top edge of the
window. Because the window is anchored to the work area with margin 0, that top
edge sits exactly on the bottom of the panel, so it reads as if the DJ were
dangling from the bar, next to the clock.

Only the body is cached. Ropes, eyes, arms and the desk EQ are cheap shapes and
are redrawn every frame.
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
    DESK_EDGE,
    DESK_FILL,
    EYE_ACCENT,
    EYE_ACCENT_DEEP,
    ROPE,
    SHELL,
    SHELL_EDGE,
    WHITE,
    lerp,
    with_alpha,
)

SIZE = QSize(200, 100)

BODY = QRectF(59.0, 20.0, 82.0, 58.0)
BODY_RADIUS = 26.0
DESK = QRectF(25.0, 76.0, 150.0, 20.0)
DESK_RADIUS = 7.0

EYE_XS = (90.0, 110.0)
EYE_Y = 48.0
EYE_W = 7.5
EYE_H = 16.0

ROPE_TOP_XS = (53.0, 147.0)
ROPE_BOTTOM_XS = (35.0, 165.0)
ROPE_BOTTOM_Y = 78.0

SHOULDER_XS = (57.0, 143.0)
SHOULDER_Y = 50.0
ARM_W = 13.0
ARM_H = 32.0

FRAME_DIRTY = QRect(0, 0, SIZE.width(), SIZE.height())
BAND_COUNT = 4
EQ_BARS = 7


class BlobAvatarRenderer:
    """Alternative avatar, selected with ``FLOATBEAT_AVATAR=blob``."""

    size = SIZE
    frame_dirty = FRAME_DIRTY
    blink_dirty = FRAME_DIRTY

    def __init__(self) -> None:
        self._body: QImage | None = None
        self._cache_key: float | None = None
        self._bands: tuple[float, ...] = (0.0,) * BAND_COUNT
        self._level = 0.0
        self._playing = True
        self._sway = 0.0
        self._now = 0.0
        self._poke_at = -10.0
        self._blink_at = -10.0

    # -- public API ---------------------------------------------------------

    def damage_rects(self, frame: int) -> list[QRect]:
        del frame
        return [FRAME_DIRTY]

    def set_frame(
        self,
        bands: Sequence[float],
        level: float,
        dt: float,
        now: float,
        playing: bool = True,
    ) -> None:
        del dt
        self._bands = tuple(bands)
        self._level = max(0.0, min(1.0, level))
        self._playing = playing
        self._now = now
        self._sway = math.sin(now * 0.9) * 1.6 * self._level if playing else 0.0

    def poke(self) -> None:
        self._poke_at = time.monotonic()
        self._blink_at = self._poke_at

    def paint(self, painter: QPainter, size: QSize) -> None:
        del size
        dpr = painter.device().devicePixelRatioF()
        if self._body is None or self._cache_key != dpr:
            self._body = self._build_body(dpr)
            self._cache_key = dpr

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        poke = self._poke()

        # Ropes: fixed at the panel edge, following the rig at the bottom.
        painter.setPen(QPen(ROPE, 1.6))
        painter.drawLine(QPointF(ROPE_TOP_XS[0], 0.0), QPointF(ROPE_BOTTOM_XS[0] + self._sway, ROPE_BOTTOM_Y))
        painter.drawLine(QPointF(ROPE_TOP_XS[1], 0.0), QPointF(ROPE_BOTTOM_XS[1] + self._sway, ROPE_BOTTOM_Y))

        painter.save()
        painter.translate(self._sway, poke * 2.0)

        self._paint_desk(painter)
        self._paint_arms(painter)
        painter.drawImage(BODY.topLeft(), self._body)
        self._paint_eyes(painter)

        painter.restore()

    # -- animated pieces ----------------------------------------------------

    def _paint_desk(self, painter: QPainter) -> None:
        path = QPainterPath()
        path.addRoundedRect(DESK, DESK_RADIUS, DESK_RADIUS)
        painter.setBrush(DESK_FILL)
        painter.setPen(QPen(DESK_EDGE, 1.0))
        painter.drawPath(path)

        values = self._eq_values() if self._playing else ()
        painter.setPen(Qt.PenStyle.NoPen)
        for i, value in enumerate(values):
            height = 2.0 + 9.0 * value
            rect = QRectF(60.5 + i * 12.0, 93.0 - height, 7.0, height)
            tint = lerp(EYE_ACCENT, WHITE, 0.55)
            painter.setBrush(with_alpha(tint, 210))
            painter.drawRoundedRect(rect, 2.0, 2.0)

        # Two small knobs at the ends of the mixer.
        painter.setBrush(with_alpha(SHELL, 205))
        painter.drawEllipse(QPointF(36.0, 86.0), 3.0, 3.0)
        painter.drawEllipse(QPointF(164.0, 86.0), 3.0, 3.0)

    def _paint_arms(self, painter: QPainter) -> None:
        low = self._bands[0] if self._bands else 0.0
        high = self._bands[3] if len(self._bands) > 3 else 0.0
        angles = (
            (-(20.0 + 10.0 * low), 20.0 + 10.0 * high)
            if self._playing
            else (-14.0, 14.0)
        )
        for shoulder_x, angle in zip(SHOULDER_XS, angles, strict=True):
            painter.save()
            painter.translate(shoulder_x, SHOULDER_Y)
            painter.rotate(angle)
            painter.setBrush(SHELL)
            painter.setPen(QPen(SHELL_EDGE, 1.0))
            painter.drawRoundedRect(QRectF(-4.0, -2.0, ARM_W, ARM_H), 7.0, 7.0)
            painter.restore()

    def _paint_eyes(self, painter: QPainter) -> None:
        blink = self._blinking()
        poke = self._poke()
        height = (EYE_H * (0.75 + 0.55 * self._level)) * (1.0 - 0.35 * poke)
        if blink:
            height = 2.0
        height = max(2.0, height)

        gaze = (self._bands[3] - self._bands[0]) * 1.2 if len(self._bands) > 3 else 0.0
        gaze = max(-2.5, min(2.5, gaze))

        gradient = QLinearGradient(0.0, -height / 2.0, 0.0, height / 2.0)
        gradient.setColorAt(0.0, lerp(EYE_ACCENT, WHITE, 0.25))
        gradient.setColorAt(1.0, EYE_ACCENT_DEEP)
        idle = QColor(138, 138, 138)
        eye_color = gradient if self._playing else idle

        for eye_x in EYE_XS:
            rect = QRectF(eye_x + gaze - EYE_W / 2.0, EYE_Y - height / 2.0, EYE_W, height)
            painter.setPen(Qt.PenStyle.NoPen)
            if self._playing:
                painter.setBrush(with_alpha(EYE_ACCENT, 45))
                painter.drawRoundedRect(rect.adjusted(-2.0, -2.0, 2.0, 2.0), 6.0, 6.0)
            painter.setBrush(eye_color)
            painter.drawRoundedRect(rect, EYE_W / 2.0, EYE_W / 2.0)
            if height > 8.0 and self._playing:
                painter.setBrush(QColor(255, 255, 255, 190))
                painter.drawEllipse(QPointF(rect.center().x(), rect.top() + 4.0), 1.1, 1.1)

    def _eq_values(self) -> tuple[float, ...]:
        bands = self._bands
        if len(bands) < 2:
            return (self._level,) * EQ_BARS
        out = []
        for i in range(EQ_BARS):
            pos = i * (len(bands) - 1) / (EQ_BARS - 1)
            left = min(int(pos), len(bands) - 2)
            t = pos - left
            out.append(bands[left] * (1.0 - t) + bands[left + 1] * t)
        return tuple(out)

    def _blinking(self) -> bool:
        if time.monotonic() - self._blink_at < 0.13:
            return True
        return (self._now % 5.4) < 0.10

    def _poke(self) -> float:
        return max(0.0, 1.0 - (time.monotonic() - self._poke_at) / 0.30)

    # -- cache --------------------------------------------------------------

    def _build_body(self, dpr: float) -> QImage:
        width = round(BODY.width() * dpr)
        height = round(BODY.height() * dpr)
        image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        image.setDevicePixelRatio(dpr)
        image.fill(Qt.GlobalColor.transparent)

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        local = QRectF(0.0, 0.0, BODY.width(), BODY.height())

        shadow = QRadialGradient(local.center() + QPointF(0.0, 6.0), BODY.width() * 0.62)
        shadow.setColorAt(0.0, QColor(0, 0, 0, 40))
        shadow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(shadow)
        painter.drawEllipse(local.adjusted(-6.0, 4.0, 6.0, 10.0))

        path = QPainterPath()
        path.addRoundedRect(local, BODY_RADIUS, BODY_RADIUS)
        painter.setBrush(SHELL)
        painter.setPen(QPen(SHELL_EDGE, 1.0))
        painter.drawPath(path)

        painter.setPen(QPen(QColor(255, 255, 255, 90), 1.0))
        painter.drawLine(
            QPointF(local.left() + 16.0, local.top() + 6.0),
            QPointF(local.right() - 16.0, local.top() + 6.0),
        )

        painter.end()
        return image

"""Render the avatar to a PNG without a window manager.

Usage:
    QT_QPA_PLATFORM=offscreen python tools/preview.py [out.png]

Used to review the drawing on a machine with no display, and to produce the
screenshot in the README. It drives the same renderer as the real widget, so
what you see here is what the desktop shows.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QGuiApplication, QLinearGradient, QPainter, QPixmap  # noqa: E402

from floatbeat.audio.demo import DemoSource  # noqa: E402
from floatbeat.ui.blob import BlobAvatarRenderer  # noqa: E402

GAP = 18
PAD = 26
COLUMNS = 4
ROWS = 1
MOMENTS = (0.20, 0.50, 0.80, 1.10)
SCALE = 2.0


def render(out: Path) -> None:
    app = QGuiApplication([])  # noqa: F841 (needed for QPixmap)
    renderer = BlobAvatarRenderer()
    tile_w = renderer.size.width()
    tile_h = renderer.size.height()
    width = PAD * 2 + COLUMNS * tile_w + (COLUMNS - 1) * GAP
    height = PAD * 2 + ROWS * tile_h + (ROWS - 1) * GAP

    canvas = QPixmap(round(width * SCALE), round(height * SCALE))
    canvas.setDevicePixelRatio(SCALE)
    canvas.fill(QColor("#0d0f16"))

    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    backdrop = QLinearGradient(QPointF(0, 0), QPointF(width, height))
    backdrop.setColorAt(0.0, QColor("#22263a"))
    backdrop.setColorAt(0.45, QColor("#151826"))
    backdrop.setColorAt(1.0, QColor("#0a0b11"))
    painter.fillRect(QRectF(0, 0, width, height), backdrop)

    # A hint of a desktop behind the widget, to judge the drop shadow and the
    # translucent console plate against something that is not flat black.
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(255, 255, 255, 8))
    painter.drawRect(QRectF(0, height * 0.72, width, height * 0.28))

    source = DemoSource()
    t = 0.0
    dt = 1.0 / 60.0
    moment_index = 0

    while moment_index < len(MOMENTS):
        if t >= MOMENTS[moment_index]:
            bands, level = source.read(0.0)
            renderer.set_frame(bands, level, dt, t)
            col = moment_index % COLUMNS
            row = moment_index // COLUMNS
            x = PAD + col * (tile_w + GAP)
            y = PAD + row * (tile_h + GAP)
            painter.save()
            painter.translate(x, y)
            renderer.paint(painter, renderer.size)
            painter.restore()
            moment_index += 1
            continue
        bands, level = source.read(dt)
        renderer.set_frame(bands, level, dt, t)
        t += dt

    painter.end()
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(str(out), "PNG")
    print(f"wrote {out} ({canvas.width()}x{canvas.height()} px)")


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "media" / "preview-blob.png"
    render(target)

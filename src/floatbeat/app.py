"""Application controller: owns the clock, the audio source and the widget.

The clock runs only while there is something to animate. Pausing stops the
QTimer and paints one resting frame, which is what brings the process back to
0% CPU (see docs/BENCHMARKS.md).
"""

from __future__ import annotations

import os
import time

from PySide6.QtCore import QObject, QSettings, Qt, QTimer

from .audio.analysis import BAND_COUNT, apply_envelope
from .audio.demo import DemoSource
from .ui.widget import FloatbeatWidget

FRAME_MS = 33  # 30 fps
IDLE_FRAME_MS = 41  # 24 fps when the mix is quiet


class FloatbeatApp(QObject):
    def __init__(self, qapp, source: DemoSource | None = None) -> None:
        super().__init__()
        self._qapp = qapp
        self._source = source if source is not None else DemoSource()
        self._settings = QSettings()
        self._widget = FloatbeatWidget(self._settings)

        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._tick)

        self._levels = [0.0] * BAND_COUNT
        self._level = 0.0
        self._now = 0.0
        self._last = 0.0
        self._paused = False
        self._quiet_frames = 0

        self._widget.pause_toggled.connect(self.set_paused)
        self._widget.quit_requested.connect(self._qapp.quit)

        self._stats_timer: QTimer | None = None
        self._frames = 0
        self._cpu0 = 0.0
        self._t0 = 0.0

    # -- lifecycle ----------------------------------------------------------

    def start(self, *, paused: bool = False) -> None:
        self._widget.restore_position()
        self._widget.show()
        if paused:
            self.set_paused(True)
        else:
            self._last = time.monotonic()
            self._timer.start(FRAME_MS)
        if os.environ.get("FLOATBEAT_STATS") == "1":
            self._stats_timer = QTimer(self)
            self._stats_timer.timeout.connect(self._report_stats)
            self._cpu0 = _self_cpu_seconds()
            self._t0 = time.monotonic()
            self._stats_timer.start(5_000)

    def stop(self) -> None:
        self._timer.stop()
        self._widget.close()

    @property
    def widget(self) -> FloatbeatWidget:
        return self._widget

    # -- contract used by the UI -------------------------------------------

    def set_paused(self, paused: bool) -> None:
        if paused == self._paused:
            self._widget.set_paused(paused)
            return
        self._paused = paused
        self._widget.set_paused(paused)
        if paused:
            self._timer.stop()
            self._widget.show_idle()
        else:
            self._last = time.monotonic()
            self._timer.start(FRAME_MS)

    # -- frame loop ---------------------------------------------------------

    def _tick(self) -> None:
        now = time.monotonic()
        dt = min(now - self._last, 0.1)
        self._last = now
        self._now += dt

        raw_bands, raw_level = self._source.read(dt)
        self._levels = [
            apply_envelope(current, target, dt)
            for current, target in zip(self._levels, raw_bands, strict=True)
        ]
        self._level = apply_envelope(self._level, raw_level, dt, attack=18.0, release=6.0)

        self._widget.set_frame(self._levels, self._level, dt, self._now)
        self._frames += 1

        # Hysteresis: toggling the interval every frame restarts the timer and
        # collapses the rate to ~25 fps. Drop to 24 fps only after a full second
        # of quiet; jump back on the first loud frame.
        if self._level > 0.5:
            self._quiet_frames = 0
        else:
            self._quiet_frames = min(self._quiet_frames + 1, 1_000)
        interval = IDLE_FRAME_MS if self._quiet_frames > 30 else FRAME_MS
        if self._timer.interval() != interval:
            self._timer.setInterval(interval)
    # -- diagnostics --------------------------------------------------------

    def _report_stats(self) -> None:
        now = time.monotonic()
        dt = max(now - self._t0, 1e-6)
        cpu = _self_cpu_seconds() - self._cpu0
        prints = self._widget.paints
        ms = (self._widget.paint_seconds / prints * 1000) if prints else 0.0
        print(
            f"fps={self._frames / dt:5.1f}  paints/s={prints / dt:5.1f}  "
            f"cpu={cpu / dt * 100:5.2f}%  paint={ms:4.2f}ms  rss={_self_rss_mb():5.1f}MB",
            flush=True,
        )
        self._frames = 0
        self._widget.paints = 0
        self._widget.paint_seconds = 0.0
        self._cpu0 = _self_cpu_seconds()
        self._t0 = now


def _self_cpu_seconds() -> float:
    times = os.times()
    return times.user + times.system


def _self_rss_mb() -> float:
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024
    except OSError:
        pass
    return 0.0

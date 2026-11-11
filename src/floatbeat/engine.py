"""Floatbeat engine: MPRIS + synthetic levels + D-Bus + the popover.

The GNOME extension is a thin renderer; this process owns the state. It exposes
``io.github.rarroy2.Floatbeat.Engine`` on the session bus:

- signal ``Frame(playing, {level, bands})`` while something is playing, and once
  when it stops (so the bar can go idle instead of polling);
- method ``ShowPopover(x, y)`` to open the mixer under the clock;
- method ``HidePopover()``.

MPRIS is polled twice per second; audio levels come from the synthetic source
until the ``parec`` capture lands.
"""

from __future__ import annotations

import argparse
import signal
import sys
import time
from collections.abc import Sequence

from PySide6.QtCore import QObject, Qt, QTimer
from PySide6.QtDBus import QDBusConnection, QDBusMessage, QDBusVirtualObject
from PySide6.QtWidgets import QApplication

from .audio.analysis import BAND_COUNT, apply_envelope
from .audio.demo import DemoSource
from .audio.mpris import MprisClient, Track
from .desktop.display import prefer_xwayland
from .ui.popover import Popover

SERVICE = "io.github.rarroy2.Floatbeat.Engine"
INTERFACE = SERVICE
OBJECT_PATH = "/io/github/rarroy2/Floatbeat/Engine"

INTROSPECT_XML = f"""
<node>
  <interface name="{INTERFACE}">
    <method name="ShowPopover">
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
    </method>
    <method name="HidePopover"/>
    <signal name="Frame">
      <arg name="playing" type="b"/>
      <arg name="data" type="a{{sv}}"/>
    </signal>
  </interface>
</node>
"""
PLAYING_MS = 40
IDLE_MS = 250
MPRIS_MS = 500


class EngineVirtualObject(QDBusVirtualObject):
    """Minimal D-Bus object with a namespaced interface name.

    PySide6 exports QObject slots under ``local.<ClassName>``, which is not a
    useful public API, so the object is registered as a virtual object and the
    introspection XML is written by hand.
    """

    def __init__(self, engine: Engine) -> None:
        super().__init__()
        self._engine = engine

    def introspect(self, path: str) -> str:
        del path
        return INTROSPECT_XML

    def handleMessage(self, message: QDBusMessage, connection: QDBusConnection) -> bool:
        if message.type() != QDBusMessage.MessageType.MethodCallMessage:
            return False
        member = message.member()
        if member == "ShowPopover":
            args = message.arguments()
            if len(args) >= 2:
                self._engine.show_popover(int(args[0]), int(args[1]))
            connection.send(message.createReply())
            return True
        if member == "HidePopover":
            self._engine.hide_popover()
            connection.send(message.createReply())
            return True
        return False


class Engine(QObject):
    def __init__(self, app: QApplication, *, demo: bool = False) -> None:
        super().__init__()
        self._app = app
        self._demo = demo
        self._mpris = MprisClient()
        self._source = DemoSource()
        self._track = Track()
        self._popover: Popover | None = None

        self._levels = [0.0] * BAND_COUNT
        self._level = 0.0
        self._now = 0.0
        self._last = time.monotonic()
        self._last_state: bool | None = None

        self._bus = QDBusConnection.sessionBus()
        self._virtual = EngineVirtualObject(self)
        if not self._bus.registerService(SERVICE):
            print(f"floatbeat-engine: cannot own {SERVICE}: {self._bus.lastError().message()}",
                  file=sys.stderr)
        self._bus.registerVirtualObject(
            OBJECT_PATH,
            self._virtual,
            QDBusConnection.VirtualObjectRegisterOption.SingleNode,
        )

        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._tick)
        self._timer.start(IDLE_MS)

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(MPRIS_MS)
        self._poll_timer.timeout.connect(self._poll)
        self._poll_timer.start()

        self._poll()

    # -- MPRIS --------------------------------------------------------------

    def _poll(self) -> None:
        track = self._mpris.refresh()
        if self._demo:
            if not track.has_track:
                track = Track(
                    title="Floatbeat Demo",
                    artist="Synthetic 124 BPM",
                    album="Floatbeat",
                    playing=True,
                )
            else:
                track.playing = True
        self._track = track
        self._update_popover_track()

    def _on_play_pause(self) -> None:
        self._mpris.play_pause()
        QTimer.singleShot(300, self._poll)

    def _on_next(self) -> None:
        self._mpris.next()
        QTimer.singleShot(400, self._poll)

    def _on_previous(self) -> None:
        self._mpris.previous()
        QTimer.singleShot(400, self._poll)

    # -- frame loop ---------------------------------------------------------

    def _tick(self) -> None:
        now = time.monotonic()
        dt = min(now - self._last, 0.1)
        self._last = now
        self._now += dt

        playing = bool(self._track.playing)
        if playing:
            raw_bands, raw_level = self._source.read(dt)
        else:
            raw_bands, raw_level = (0.0,) * BAND_COUNT, 0.0

        self._levels = [
            apply_envelope(current, target, dt)
            for current, target in zip(self._levels, raw_bands, strict=True)
        ]
        self._level = apply_envelope(self._level, raw_level, dt, attack=18.0, release=6.0)

        if playing:
            self._emit(True)
        elif self._last_state is not False:
            self._emit(False)

        if self._popover is not None and self._popover.isVisible():
            self._popover.set_frame(self._levels, self._level, dt, self._now, playing)

        interval = PLAYING_MS if playing else IDLE_MS
        if self._timer.interval() != interval:
            self._timer.setInterval(interval)

    def _emit(self, playing: bool) -> None:
        self._last_state = playing
        message = QDBusMessage.createSignal(OBJECT_PATH, INTERFACE, "Frame")
        message << playing << {
            "level": float(self._level) if playing else 0.0,
            "bands": [float(value) for value in self._levels] if playing
            else [0.0] * BAND_COUNT,
        }
        self._bus.send(message)

    # -- popover ------------------------------------------------------------

    def show_popover(self, x: int, y: int) -> None:
        if self._popover is None:
            self._popover = Popover()
            self._popover.play_pause.connect(self._on_play_pause)
            self._popover.next_track.connect(self._on_next)
            self._popover.previous_track.connect(self._on_previous)
        self._poll()
        self._popover.show_at(x, y)
        self._popover.set_frame(
            self._levels, self._level, 0.0, self._now, bool(self._track.playing)
        )

    def hide_popover(self) -> None:
        if self._popover is not None:
            self._popover.close()

    def _update_popover_track(self) -> None:
        if self._popover is None:
            return
        track = self._track
        self._popover.set_track(
            title=track.title,
            artist=track.artist,
            album=track.album,
            art_url=track.art_url,
            position_us=track.position_us,
            length_us=track.length_us,
            playing=track.playing,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="floatbeat-engine")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="force the synthetic track and levels even when no player is active",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args, qt_args = build_parser().parse_known_args(argv)
    prefer_xwayland()

    app = QApplication([sys.argv[0], *qt_args])
    app.setApplicationName("Floatbeat")
    app.setApplicationDisplayName("Floatbeat")
    app.setOrganizationName("Floatbeat")
    app.setOrganizationDomain("github.com/rarroy2")
    app.setDesktopFileName("io.github.rarroy2.Floatbeat")
    app.setQuitOnLastWindowClosed(False)
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    engine = Engine(app, demo=args.demo)  # noqa: F841 (kept alive by the loop)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

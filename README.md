# Floatbeat

> A tiny DJ that lives on your Linux desktop and moves to whatever is playing.

**Status: v0.1.0 — Phase 1.** The floating window, the procedural avatar and the
demo signal are working. Real audio capture and MPRIS metadata are next
(see [`docs/SPEC.md`](docs/SPEC.md)).

Full usage guide, FAQ and troubleshooting: [`docs/USAGE.md`](docs/USAGE.md).

![Floatbeat avatar reacting to the demo signal](docs/media/preview.png)

Floatbeat is a frameless, transparent, always-on-top widget: a small cube-shaped
DJ with a visor for eyes that bobs and scratches to the audio coming out of your
machine, while showing what is playing and letting you control it. When nothing
is playing, it stops drawing entirely.

## Try it

```bash
git clone https://github.com/rarroy2/floatbeat.git
cd floatbeat
uv venv --python 3.13
uv pip install -e ".[dev]"
python -m floatbeat
```

- **Drag** anywhere on the character to move it.
- **Click** to poke it.
- **Right-click** for the menu: pause, corner anchor, quit.
- It starts in the **top-right of the work area**, just below the panel (the bar
  with the clock on GNOME), and follows the panel if you move it.

```bash
python -m floatbeat --no-demo   # resting pose, render timer stopped
FLOATBEAT_STATS=1 python -m floatbeat   # print fps / CPU / RSS every 5 s
```

The animation comes from a synthetic 124 BPM source until the real capture
lands: kick, snare, hats and a bass swell, so the bars, the eyes and the LED have
something musical to react to.

## Why another desktop pet?

Most "notch companion" apps are macOS-first, or they decorate a bar instead of
living on the desktop. Floatbeat is built the other way around:

- **Linux first**: MPRIS2 over D-Bus for metadata and controls, PipeWire or
  PulseAudio for the audio signal.
- **Signal-driven, not timer-driven**: the animation clock only runs while there
  is audio. Paused means zero repaints.
- **No portable-runtime blur**: rendered with `QPainter`, not GIFs or Lottie, so
  edges stay clean on any DPI.
- **Small surface, honest budget**: one widget, no web engine, no Electron.

## How it works

```
┌──────────────────┐     PropertiesChanged     ┌──────────────────┐
│  MPRIS2 players   │ ────────(QtDBus)────────▶ │                  │
│  Spotify, VLC,    │                           │   PlayerState    │
│  Firefox, …       │ ◀──── Play()/Pause()────── │  (single source  │
└──────────────────┘                           │   of truth)      │
                                               │        │         │
┌──────────────────┐     PCM 44.1 kHz mono     │        ▼         │
│  sink.monitor     │ ────────(parec)─────────▶ │  RMS + bands     │
└──────────────────┘                           └────────┬─────────┘
                                                        │ 30 fps
                                                        ▼
                                               ┌──────────────────┐
                                               │  QPainter avatar │
                                               │  + bars + panel  │
                                               └──────────────────┘
```

The audio level is authoritative: if there is signal, the widget animates even
when no MPRIS player is publishing metadata (games, browsers, calls). MPRIS
enriches and controls; it does not gate the animation.

## What it costs you

Measured on GNOME/Wayland (XWayland), 12 threads, 1920×1080 @ 1×, PySide6 6.12
on CPython 3.14. Full methodology and the optimisation log in
[`docs/BENCHMARKS.md`](docs/BENCHMARKS.md).

| Metric | Measured | What it means |
| --- | --- | --- |
| CPU, 30 fps | 6.4 % of one core | **0.53 % of a 12-thread machine.** GNOME Shell measured 16.2 % on the same box |
| CPU, paused | 0.00 % | Timer stopped; the process sleeps |
| RSS / PSS | 85.6 / 55.9 MB | About one browser tab; most of it is shared Qt |
| Paint time | 1.33 ms / frame | 30 fps with headroom |

The percentage is **of a single core**, the unit `top` and `htop` show. In
practice you will not notice the widget running, and it disappears completely
when playback stops. It is not free on battery — roughly the same order as a
blinking desktop clock — and pausing it takes one click.

A 40 MB target is not reachable with Qt: importing `PySide6.QtWidgets` alone
costs 43.8 MB RSS before any window exists, and 3 % of a core is below the floor
of the widget stack (~2.7 % before drawing anything). The numbers above are the
honest ones, reproducible with `FLOATBEAT_STATS=1`.

## Requirements

- Linux (X11 or XWayland). Native Wayland works, with documented limits.
- PipeWire or PulseAudio, with a monitor source on the default sink.
- Python 3.12+ (PySide6 6.12 wheels are available for 3.14).
- D-Bus session bus for MPRIS.

## Where it sits

The widget anchors to the **work area**, the part of the screen your desktop
leaves free after panels and docks. On GNOME that means it appears right under
the 32 px top bar, next to the clock area; on KDE or XFCE it follows the panel
wherever you put it. Right-click → *Posición en pantalla* snaps it to any corner.

It cannot live *inside* the panel: that is a plugin, not a window, and each
desktop implements panels differently (GNOME Shell extension, KDE plasmoid,
XFCE plugin). The work-area anchor is one implementation that works everywhere.

## Wayland note

A Wayland client cannot choose its own position or stacking order, so Floatbeat
starts under **XWayland by default** when both backends are present. If you want
the native path anyway:

```bash
FLOATBEAT_NATIVE_WAYLAND=1 python -m floatbeat
```

Expect the compositor to place the widget where it wants. Details in
[`docs/DECISIONS.md`](docs/DECISIONS.md) (ADR-003).

## Project layout

```
floatbeat/
├── src/floatbeat/
│   ├── __main__.py        # CLI and QApplication lifecycle
│   ├── app.py             # clock, state, frame loop
│   ├── ui/
│   │   ├── widget.py      # frameless window, drag, menu, position memory
│   │   ├── avatar.py      # procedural cube + visor + bars (QPainter)
│   │   └── theme.py       # palette
│   ├── audio/
│   │   ├── analysis.py    # RMS, envelope, 4-band split (no Qt)
│   │   └── demo.py        # synthetic 124 BPM source
│   └── desktop/
│       └── display.py     # XWayland preference, position restore
├── tools/preview.py       # render the avatar to PNG without a display
├── tests/
└── docs/
```

## Roadmap

- [x] Validate the stack and measure the real cost
- [x] Write the corrected specification
- [x] Phase 1 — floating window + procedural avatar + oscillator (v0.1.0)
- [ ] Phase 2 — MPRIS2 metadata and controls
- [ ] Phase 3 — system audio capture + bands
- [ ] Phase 4 — expandable panel and settings
- [ ] Phase 5 — Flatpak + AppImage
- [ ] Later — Windows port (GSMTC + WASAPI loopback)

## Design and originality

Floatbeat's initial inspiration is [Coucou](https://github.com/louis-cfm/coucou)
by Louis Raillé (MIT code, reserved name and assets). Floatbeat **does not reuse
any Coucou code, art, sound or naming**, and is deliberately built around a
different silhouette (beveled cube, headphone band, single wrap-around visor)
and a different animation language. The credit is here because honesty about
inspiration is cheaper than defending a clone accusation.

## License

Code under the [MIT License](LICENSE). Artwork and sounds, when they exist, will
be released under their own license file.

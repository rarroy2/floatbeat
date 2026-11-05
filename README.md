# Floatbeat

> A tiny DJ that lives on your Linux desktop and moves to whatever is playing.

**Status: alpha — Phase 1.** The floating window, the procedural avatar and the
demo signal are working. Real audio capture and MPRIS metadata are next
(see [`docs/SPEC.md`](docs/SPEC.md)).

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
- **Right-click** for the menu: pause, reset position, quit.

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

## Performance budget

Measured on GNOME/Wayland (XWayland), 12 threads, 1920×1080 @ 1×, PySide6 6.12
on CPython 3.14. Full methodology and the optimisation log in
[`docs/BENCHMARKS.md`](docs/BENCHMARKS.md).

| Metric | Phase 1 | Budget |
| --- | --- | --- |
| RSS, animating | 85.6 MB | ≤ 120 MB |
| PSS, animating | 55.9 MB | ≤ 65 MB |
| CPU, 30 fps | 6.3–6.5 % of one core | ≤ 7 % |
| CPU, paused | 0.00 % | ≈ 0 % |
| Paint time | 1.3 ms / frame | ≤ 2 ms |

A 40 MB target is not reachable with Qt: importing `PySide6.QtWidgets` alone
costs 43.8 MB RSS before any window exists. The budget above is the honest one.

## Requirements

- Linux (X11 or XWayland). Native Wayland works, with documented limits.
- PipeWire or PulseAudio, with a monitor source on the default sink.
- Python 3.12+ (PySide6 6.12 wheels are available for 3.14).
- D-Bus session bus for MPRIS.

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
- [x] Phase 1 — floating window + procedural avatar + oscillator
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

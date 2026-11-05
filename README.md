# Floatbeat

> A tiny DJ that lives on your Linux desktop and moves to whatever is playing.

**Status: pre-alpha — specification phase.** There is no runnable code yet. The
architecture, performance budget and scope are being validated before the first
line ships (see [`docs/SPEC.md`](docs/SPEC.md) and
[`docs/DECISIONS.md`](docs/DECISIONS.md)).

Floatbeat is a frameless, transparent, always-on-top widget: a small cube-shaped
DJ with a visor for eyes that bobs and scratches to the audio coming out of your
machine, while showing what is playing and letting you control it. When nothing
is playing, it stops drawing entirely.

## Why another desktop pet?

Most "notch companion" apps are macOS-first, or they decorate a bar instead of
living on the desktop. Floatbeat is built the other way around:

- **Linux first**: MPRIS2 over D-Bus for metadata and controls, PipeWire or
  PulseAudio for the audio signal.
- **Signal-driven, not timer-driven**: the animation clock only runs while there
  is actual audio. Paused means zero repaints.
- **No portable-runtime blur**: rendered with `QPainter`, not GIFs or Lottie, so
  edges stay clean on any DPI.
- **Small surface, honest budget**: one widget, no web engine, no Electron.

## Planned features (v0.1)

- Borderless, transparent window that stays on top and can be dragged.
- Reactive visualizer driven by the system output monitor (3–5 bands).
- MPRIS2 metadata: title, artist, album art, playback status.
- Playback controls: play/pause, previous/next, seek.
- Expandable panel on click, with a settings page.
- Eyes follow the cursor (opt-in, throttled to 20 Hz).
- Idle mode stops the render timer and releases the audio stream.

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

Measured on GNOME/Wayland (XWayland), 12 threads, 1920×1080 @ 1× with a
throwaway 220×220 prototype. Full methodology in
[`docs/BENCHMARKS.md`](docs/BENCHMARKS.md).

| Metric | Prototype (naive) | Budget v0.1 |
| --- | --- | --- |
| RSS, window visible | 83 MB | ≤ 120 MB |
| PSS, window visible | 53.5 MB | ≤ 65 MB |
| CPU, 30 fps | 5.7–7.7 % of one core | ≤ 3 % |
| CPU, paused | 0.00–0.24 % | ≈ 0 % |

A 40 MB target is not reachable with Qt: importing `PySide6.QtWidgets` alone
costs 43.8 MB RSS before any window exists. The budget above is the honest one.

## Requirements

- Linux (X11 or XWayland). Native Wayland works, with documented limits.
- PipeWire or PulseAudio, with a monitor source on the default sink.
- Python 3.12+ (PySide6 6.12 wheels are available for 3.14).
- D-Bus session bus for MPRIS.

## Development

```bash
git clone https://github.com/rarroy2/floatbeat.git
cd floatbeat
uv venv --python 3.13
uv pip install -e ".[dev]"
python -m floatbeat
```

Until Phase 1 lands, `python -m floatbeat` does nothing: the package does not
exist yet.

## Project layout (planned)

```
floatbeat/
├── src/floatbeat/
│   ├── __main__.py        # QApplication lifecycle
│   ├── ui/widget.py       # frameless window, drag, expand/collapse
│   ├── ui/avatar.py       # procedural DJ + bars (QPainter)
│   ├── ui/panel.py        # metadata, controls, settings
│   ├── audio/mpris.py     # QtDBus MPRIS2 client
│   ├── audio/capture.py   # parec subprocess → PCM frames
│   └── audio/analysis.py  # RMS + band energy
├── assets/                # icon, .desktop, metainfo
├── packaging/             # flatpak manifest, AppImage recipe
├── docs/
└── tests/
```

## Roadmap

- [x] Validate the stack and measure the real cost
- [x] Write the corrected specification
- [ ] Phase 1 — floating window + procedural avatar + oscillator
- [ ] Phase 2 — MPRIS2 metadata and controls
- [ ] Phase 3 — system audio capture + bands
- [ ] Phase 4 — expandable panel and settings
- [ ] Phase 5 — Flatpak + AppImage
- [ ] Later — Windows port (GSMTC + WASAPI loopback)

## Design and originality

Floatbeat's initial inspiration is [Coucou](https://github.com/louis-cfm/coucou)
by Louis Raillé (MIT code, reserved name and assets). Floatbeat **does not reuse
any Coucou code, art, sound or naming**, and is deliberately built around a
different silhouette (beveled cube, single wrap-around visor) and a different
animation language. The credit is here because honesty about inspiration is
cheaper than defending a clone accusation.

## License

Code under the [MIT License](LICENSE). Artwork and sounds, when they exist, will
be released under their own license file.

# Floatbeat

> A tiny DJ living in your GNOME top bar.

**Status: v0.2.0-alpha.1 — GNOME Shell extension spike.** The mini DJ is already
hanging next to the clock. The idle/playing states, the Python engine and the
translucent mixer are the next steps.

![Floatbeat mini avatar in the top bar](docs/media/preview-mini.png)

Floatbeat started as a floating window (v0.1.0) and pivoted to a GNOME Shell
extension: a window that is always visible *without covering window titles* can
only live in space the desktop already reserves — the panel. The full story is
in [`docs/DECISIONS.md`](docs/DECISIONS.md) (ADR-015).

## What works right now

- A 56×38 actor in the top panel, just left of the clock, drawn with Cairo.
- It overflows 6 px below the bar: the panel does not clip its children, so the
  mixer desk appears to dangle from the edge.
- 25 fps animation driven by a synthetic signal, with cyan eyes, arms that lean
  with the beat and a five-bar EQ.
- Clicking it is wired (it currently logs and blinks; the engine call lands next).
- The blob renderer for the future popover is in place and previewed below.

![Blob avatar for the popover](docs/media/preview-blob.png)

## What's next

1. **Idle state**: when nothing is playing, grey eyes, no bars, no animation.
2. **Python engine**: MPRIS2 metadata/controls plus a D-Bus service that
   publishes the audio level. The bar stays in GJS; the engine does the rest.
3. **Translucent popover**: big character, album art, title, artist and playback
   controls, opened by clicking the desk.
4. **Real audio**: replace the synthetic source with `parec` on the sink monitor.
5. **Packaging**: extension zip, engine as a systemd user service, release flow.

## Install (extension)

```bash
./extension/install.sh
# GNOME only scans extensions at login:
# log out and back in
gnome-extensions enable floatbeat@rarroy2.github.io
```

Tested on GNOME Shell 50.6 (Wayland). The extension declares support for 45–50.

To disable:

```bash
gnome-extensions disable floatbeat@rarroy2.github.io
```

## Requirements

- GNOME Shell 45–50.
- No Python process is needed for the bar itself; the engine will be optional
  until the audio/MPRIS work lands.

## Project layout

```
floatbeat/
├── extension/            # GNOME Shell extension (GJS + Cairo)
│   ├── extension.js      # panel placement, timer, click
│   ├── avatar.js         # mini avatar drawing (56×38 design space)
│   └── install.sh
├── src/floatbeat/
│   ├── audio/            # RMS + bands + synthetic source (reused by the engine)
│   ├── ui/blob.py        # avatar for the popover
│   ├── ui/theme.py
│   └── desktop/          # XWayland preference and screen helpers
├── tools/preview.py      # render the popover avatar to PNG
├── tests/
└── docs/
```

The original floating-window app lives in the `v0.1.0` tag. It is kept as
history: it proved the rendering budget (1.33 ms/frame, 6.4 % of one core) and
the reasons why a normal window cannot satisfy the "always visible, never in the
way" requirement.

## Why the pivot

- A normal window cannot sit inside the GNOME bar: the shell draws the panel above
  every client.
- Any window just below the bar covers the title bar of maximised windows.
- The only space that is always visible and reserved is the panel, and the panel
  is 32 px tall.

So the character lives in the panel at bar scale, with an optional overflow of a
few pixels, and the full-size version moves into a popover. Details, measurements
and rejected alternatives: [`docs/DECISIONS.md`](docs/DECISIONS.md) ADR-015.

## Performance

The extension draws a 56×38 Cairo surface at 25 fps only while it has something
to animate; the idle path will stop the timer entirely. The Python engine and the
popover will be measured when they land. Historical numbers for the v0.1.0 app
are in [`docs/BENCHMARKS.md`](docs/BENCHMARKS.md).

## License

Code under the [MIT License](LICENSE). Artwork, when it exists, will be released
under its own license file.

# Using Floatbeat

Floatbeat is a small window, not a panel applet: it floats above the other
windows, it can be dragged anywhere, and it can snap to a corner of your work
area. This guide covers what it does today (v0.1) and the questions that come up
most often.

## Install and run

Floatbeat is not packaged yet (that is Phase 5). From a checkout:

```bash
git clone https://github.com/rarroy2/floatbeat.git
cd floatbeat
uv venv --python 3.13
uv pip install -e ".[dev]"
python -m floatbeat
```

With `pip` instead of `uv`:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
python -m floatbeat
```

Useful flags:

| Flag / variable | Effect |
| --- | --- |
| `--no-demo` | Start paused in the resting pose (render timer stopped) |
| `--version` | Print the version |
| `FLOATBEAT_STATS=1` | Print fps, paints/s, CPU, paint time and RSS every 5 s |
| `FLOATBEAT_NATIVE_WAYLAND=1` | Use the native Wayland backend instead of XWayland |

## Controls

| Action | Result |
| --- | --- |
| Drag the character | Move the window |
| Left click | Poke it (it blinks and bounces) |
| Right click | Menu: pause, position, quit |
| Right click → Posición en pantalla | Snap to a corner of the work area |

The window remembers its position between runs. Moving it by hand does not
change the selected anchor: the anchor is where "snap" goes, not a lock.

## Where it sits on screen

The default is **top-right of the work area**. The work area is the part of the
screen your desktop leaves free after panels and docks, so Floatbeat lands just
below the top bar on GNOME (the bar with the clock) and follows the panel if you
move it to the bottom or the left on KDE, XFCE or Cinnamon. There is nothing to
configure on first run.

If your panel is on the right and you want the widget under it, pick
"Arriba derecha" and increase the margin by editing `window/margin` in
`~/.config/Floatbeat/Floatbeat.conf` (default 24 px).

> **Why not inside the bar, next to the clock?** That is not a floating window,
> it is a panel plugin. Every desktop implements panels differently, so it would
> need a GNOME Shell extension plus a KDE plasmoid plus an XFCE plugin — three
> separate codebases. The work-area anchor gives 95 % of the effect with one
> implementation. A panel plugin is a possible future project, not a setting.

## What it costs

Measured on GNOME/Wayland via XWayland, 12 threads, 1920×1080, PySide6 6.12 on
CPython 3.14. Full method and every optimisation step in
[`BENCHMARKS.md`](BENCHMARKS.md).

| Metric | Measured | What it means |
| --- | --- | --- |
| CPU while animating at 30 fps | 6.4 % of one core | **0.53 % of a 12-thread CPU.** For comparison, GNOME Shell measured 16.2 % on the same machine |
| CPU while paused / silent | 0.00 % | The timer stops and the process sleeps; no repaints at all |
| RAM (RSS / PSS) | 85.6 / 55.9 MB | About one browser tab; most of it is Qt shared with other apps |
| Paint time | 1.33 ms per frame | 30 fps with headroom |
| Startup | under 1 s | No background service, no index, no cache to warm |

The 6.4 % figure sounds bigger than it feels because it is **a percentage of a
single core**, the unit `top` and `htop` use. On a 12-thread laptop that is half
a percent of the machine, and it disappears entirely the moment playback stops.

It is not free, though: on battery, a continuously animating widget costs roughly
the same order as a blinking desktop clock. If you care about every watt, pause
it from the right-click menu (or start with `--no-demo`); the cost goes to zero.

## Troubleshooting

### The widget appears in the wrong place

You are probably on native Wayland, where a client cannot choose its position.
Unset `FLOATBEAT_NATIVE_WAYLAND` so Floatbeat uses XWayland, then right-click →
Posición en pantalla → pick a corner.

### The window is blurry

XWayland does not always pick up the compositor's scale factor. Try:

```bash
QT_SCALE_FACTOR=1.5 python -m floatbeat
```

(Replace 1.5 with your monitor scale.) Native Wayland handles HiDPI better but
loses absolute positioning.

### Nothing reacts to my music

Expected in v0.1: audio capture lands in Phase 3. The motion you see comes from
a synthetic 124 BPM demo source, so the visualiser can be developed and measured
without touching your audio.

### It does not appear on the second monitor

Drag it there. The anchor menu uses the primary screen's work area; manual
positions on any screen are remembered.

### The right-click menu does not open

The window is only 220×220 px. Right-click on the character itself, not on the
transparent margin around it.

## FAQ

**Does it need Spotify?** No. v0.1 does not talk to any player. Phase 2 adds
MPRIS2 (Spotify, VLC, Firefox, Chromium, mpv…) and Phase 3 adds system audio, so
games and calls work too.

**Does it send anything to the internet?** No. There is no telemetry, no account
and no network code in v0.1.

**Why Python and Qt if the RAM target is low?** Because the alternative was a
different toolkit, not a better widget: importing PySide6 alone costs 43.8 MB
before any window exists. The trade-off is documented in
[`DECISIONS.md`](DECISIONS.md) (ADR-001/ADR-002).

**Why 6 % and not 3 %?** The original budget was 3 %; measurement showed the
floor of Qt widgets is ~2.7 % before drawing anything. The honest budget is 7 %,
and every step to get there is in [`BENCHMARKS.md`](BENCHMARKS.md). The README
does not promise numbers it cannot reproduce.

**Can I have two instances?** Not yet; there is no single-instance lock. It is
on the Phase 4 list.

**Will it run on Windows?** The UI already is portable Qt. Audio capture and
metadata need native APIs (WASAPI loopback and GSMTC); that is a post-1.0 task,
not a rewrite.

## Reporting problems

Open an issue at <https://github.com/rarroy2/floatbeat/issues> with:

- your desktop and session type (`echo $XDG_CURRENT_DESKTOP $XDG_SESSION_TYPE`),
- the output of `python -m floatbeat --version`,
- and, if it is a performance problem, the lines printed with
  `FLOATBEAT_STATS=1`.

# Using Floatbeat

Floatbeat is a GNOME Shell extension (a tiny DJ in the top bar) plus a Python
engine that reads MPRIS and opens the mixer popover.

## Install

### Extension

```bash
git clone https://github.com/rarroy2/floatbeat.git
cd floatbeat
./extension/install.sh
```

GNOME only scans the extensions directory at login, so **log out and back in**.
Then:

```bash
gnome-extensions enable floatbeat@rarroy2.github.io
```

### Engine

```bash
uv pip install -e .
.venv/bin/floatbeat-engine
```

Keep it running in a terminal (it will become a systemd user service in the
packaging phase). For testing without a player:

```bash
.venv/bin/floatbeat-engine --demo
```

## What you see

- **Nothing playing**: grey eyes, empty mixer, no animation, and the extension
  stops its render timer.
- **Playing**: cyan glowing eyes, equaliser bars, arms moving with the beat.
- **Click the character**: opens the translucent popover under the clock with the
  big avatar, album art, title/artist/album, progress and controls.
- **Controls**: previous, play/pause and next act on the active MPRIS player.
  Click outside or press Escape to close.

If the engine is not running, the character stays in the idle state. That is
intentional: the bar never depends on Python to exist.

## Controls

| Action | Result |
| --- | --- |
| Click the character | Open the mixer popover |
| Click outside / Escape | Close the popover |
| Popover buttons | Previous / play-pause / next |
| Disable | `gnome-extensions disable floatbeat@rarroy2.github.io` |

## Troubleshooting

### Nothing ever turns cyan

The engine is not running, or no MPRIS player reports `Playing`.

```bash
pgrep -af floatbeat-engine
gdbus introspect --session \
  --dest io.github.rarroy2.Floatbeat.Engine \
  --object-path /io/github/rarroy2/Floatbeat/Engine
```

Start it with `.venv/bin/floatbeat-engine` (or `--demo` to force the synthetic
track).

### The popover does not appear

- The extension must be the current version: log out and back in after
  `./extension/install.sh`.
- The engine must be running.
- The popover is a normal window under XWayland; if you force native Wayland
  (`FLOATBEAT_NATIVE_WAYLAND=1` for the old app) positioning is up to the
  compositor. The engine uses XWayland by default.

### It does not appear after login

```bash
gnome-extensions info floatbeat@rarroy2.github.io
journalctl --user -b -o cat /usr/bin/gnome-shell | grep -i floatbeat | tail -30
```

If `State` is `ERROR`, the journal has the stack trace. Disable it with
`gnome-extensions disable ...` while fixing it.

### It is cut off at the bottom

Some GNOME versions or themes may clip panel children that overflow. Reduce
`OVERFLOW` in `extension/avatar.js` from 6 to 0; the character then fits inside
the 32 px bar.

### I changed the extension and nothing happens

GNOME 50 does not implement `ReloadExtension`: log out and back in after
`./extension/install.sh`. For quick visual checks, render the avatar outside the
shell with GJS + Cairo (see `extension/README.md`).

## Reporting problems

Open an issue at <https://github.com/rarroy2/floatbeat/issues> with:

- `gnome-shell --version` and `echo $XDG_SESSION_TYPE`,
- `gnome-extensions info floatbeat@rarroy2.github.io`,
- the journal lines above,
- and the engine output if it is a metadata/controls problem.

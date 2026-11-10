# Using Floatbeat

Floatbeat is a GNOME Shell extension: a tiny DJ that hangs in the top bar, left
of the clock. It is not a floating window anymore (that was v0.1.0; see the tag).

## Install

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

It should appear immediately, to the left of the clock.

## What you see now (v0.2.0-alpha.1)

- A 56×38 DJ with white body, cyan eyes, little arms and a mixer desk that
  dangles 6 px below the bar.
- It animates at 25 fps with a synthetic signal. Real playback comes with the
  engine in the next phase.
- Clicking it currently logs `[floatbeat] clicked` in the journal and makes the
  character blink. The popover lands next.

The idle state (grey eyes, no bars, no animation when nothing is playing) and the
translucent popover with album art and controls are the immediate next steps.

## Disable or uninstall

```bash
gnome-extensions disable floatbeat@rarroy2.github.io
```

To remove it completely:

```bash
rm -rf ~/.local/share/gnome-shell/extensions/floatbeat@rarroy2.github.io
```

You may also want to remove it from `org.gnome.shell enabled-extensions` in the
Extensions app, or with `gsettings`.

## Troubleshooting

### It does not appear after login

```bash
gnome-extensions info floatbeat@rarroy2.github.io
journalctl --user -b -o cat /usr/bin/gnome-shell | grep -i floatbeat | tail -30
```

If `State` is `ERROR`, the journal has the stack trace. Disable it with
`gnome-extensions disable ...` while fixing it.

### It is cut off at the bottom

Some GNOME versions or themes may clip panel children that overflow. The fix is
to reduce `OVERFLOW` in `extension/avatar.js` from 6 to 0; the character then
fits entirely inside the 32 px bar.

### It sits in the wrong place

The actor is positioned from `Main.panel.statusArea.dateMenu`. If the clock is
missing (unusual layouts), it falls back to the centre of the primary monitor.

### I changed the code and nothing happens

GNOME 50 does not implement `ReloadExtension`. Log out and back in after
`./extension/install.sh`. For quick visual checks, the drawing can be rendered
outside the shell:

```bash
gjs -m /tmp/mini_preview.mjs   # see extension/README.md
```

### Does it need Python?

Not for the bar. The Python engine (MPRIS, audio levels, popover) is optional and
lands in the next phase. Without it the extension shows the idle state.

## Reporting problems

Open an issue at <https://github.com/rarroy2/floatbeat/issues> with:

- `gnome-shell --version` and your session type (`echo $XDG_SESSION_TYPE`),
- the output of `gnome-extensions info floatbeat@rarroy2.github.io`,
- and the journal lines above.

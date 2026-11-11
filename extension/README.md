# Floatbeat — GNOME Shell extension (spike)

Draws a tiny DJ in the top panel, left of the clock. The actor lives in the
shell UI group anchored to the panel, so it can overflow a few pixels below the
bar (the panel does not clip its children).

## Install

```bash
./extension/install.sh
# log out and back in (GNOME scans extensions at login)
gnome-extensions enable floatbeat@rarroy2.github.io
```

## Development

- The drawing lives in `avatar.js` (Cairo, 56×38 design space).
- `extension.js` handles panel placement, the animation timer and the click.
- Edit, run `./extension/install.sh`, then log out/in to reload.
- Errors: `journalctl --user -b -o cat /usr/bin/gnome-shell | grep -i floatbeat`
  or `gnome-extensions info floatbeat@rarroy2.github.io`.

Clicking the character calls `ShowPopover` on the Python engine and opens the
translucent mixer. Without the engine the actor stays idle (grey eyes, no bars).

## Engine

```bash
uv pip install -e ..
.venv/bin/floatbeat-engine          # real MPRIS
.venv/bin/floatbeat-engine --demo    # synthetic track for development
```

The extension watches `io.github.rarroy2.Floatbeat.Engine` on the session bus;
when it appears it subscribes to `Frame(playing, {level, bands})` and switches
between idle and playing.

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

The click currently logs `[floatbeat] clicked`; it will call the Python engine
over D-Bus once that exists.

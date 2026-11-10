# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0-alpha.1] - 2026-11-10

### Added

- GNOME Shell extension spike: a 56×38 Cairo actor in the top panel, left of the
  clock, with 6 px of overflow below the bar.
- `extension/avatar.js` mini avatar with cyan eyes, arms and a mixer desk.
- Blob avatar renderer for the future popover, with swaying ropes and a hue-only
  eye accent.
- Previews for the mini avatar and the popover avatar.

### Changed

- **Pivot**: the project is now a GNOME Shell extension plus a Python engine and
  a translucent popover. A normal window cannot be always visible without
  covering window titles (ADR-015).
- Repository restructured around `extension/` and the reusable engine modules.

### Removed

- The Qt floating-window app from `main`. It is preserved in the `v0.1.0` tag.

### Added

- Position anchors: the widget snaps to any corner of the work area and defaults
  to the top-right, just below the panel.

### Changed

- First run now ignores a stale saved position from pre-0.1.0 builds and uses the
  new anchor instead.

### Documentation

- `docs/USAGE.md`: controls, positioning, real performance numbers, FAQ and
  troubleshooting.
- `CONTRIBUTING.md`: branch naming, Conventional Commits and SemVer rules.
- README performance section now explains what 6.4 % of one core means in
  practice instead of only listing the number.

## [0.1.0] - 2026-11-06

### Added

- Frameless, transparent, always-on-top window with drag support
  (`startSystemMove` plus a manual fallback) and position memory.
- Procedural avatar drawn with `QPainter`: beveled cube, headphone band, visor
  with reactive eyes, five-band EQ and a beat LED.
- Synthetic 124 BPM source (kick, snare, hats, bass) so the UI can be developed
  and measured without capturing system audio.
- Attack/release envelope smoothing and a 30/24 fps hysteresis loop.
- Streaming 4-band analyser and RMS helpers, independent of Qt.
- Right-click menu with pause and quit; left click makes the character react.
- Cached body and visor plate, single damage rect per frame: 1.33 ms of paint per
  frame, 6.4 % of one core at 30 fps, 0.00 % when paused.
- `FLOATBEAT_STATS=1` diagnostics and `tools/preview.py` to render the avatar to
  a PNG without a display.

[Unreleased]: https://github.com/rarroy2/floatbeat/compare/v0.2.0-alpha.1...HEAD
[0.2.0-alpha.1]: https://github.com/rarroy2/floatbeat/releases/tag/v0.2.0-alpha.1
[0.1.0]: https://github.com/rarroy2/floatbeat/releases/tag/v0.1.0

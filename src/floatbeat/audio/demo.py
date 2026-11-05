"""Synthetic audio source used to develop the UI without touching the system.

It models a 124 BPM track: kick on every beat, snare on 2 and 4, eighth-note
hats and a slow bass swell, plus a small "drop" every eight bars. Deterministic
for a given ``bpm`` so tests and previews are reproducible.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

BPM = 124.0


@dataclass(slots=True)
class DemoSource:
    bpm: float = BPM
    t: float = 0.0

    def read(self, dt: float) -> tuple[tuple[float, ...], float]:
        """Advance ``dt`` seconds and return (bands, level) in 0..1."""
        self.t += max(dt, 0.0)
        beat = self.t * self.bpm / 60.0
        beat_index = int(beat)
        bar = beat_index // 4
        drop = 1.15 if bar % 8 >= 6 else 1.0

        kick = math.exp(-7.0 * (beat % 1.0)) * 0.92 * drop
        snare_gate = 1.0 if beat_index % 4 in (1, 3) else 0.0
        snare = math.exp(-12.0 * ((beat + 0.5) % 1.0)) * 0.85 * snare_gate
        hat = math.exp(-27.0 * ((beat * 2.0) % 1.0)) * 0.5
        bass = (0.5 + 0.5 * math.sin(self.t * 1.9 + 0.6)) * 0.45
        lead = (0.5 + 0.5 * math.sin(self.t * 3.1)) * (0.18 if bar % 4 in (2, 3) else 0.07)

        low = _unit(kick * 0.85 + bass * 0.35)
        low_mid = _unit(0.18 + bass * 0.55 + kick * 0.25)
        high_mid = _unit(snare * 0.95 + lead * 0.5)
        high = _unit(hat * 0.95 + lead * 0.35)
        level = _unit(
            0.12 + max(kick * 0.95, snare * 0.70, hat * 0.30, bass * 0.55, lead * 0.40)
        )
        return (low, low_mid, high_mid, high), level


def _unit(value: float) -> float:
    return max(0.0, min(1.0, value))

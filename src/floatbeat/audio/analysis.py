"""Low-level audio analysis.

Kept free of Qt so it can be unit-tested and reused by any capture backend.

The band split is intentionally cheap: three cascaded one-pole low-passes give
four contiguous bands. That is plenty for four or five decorative bars and costs
a few multiplications per sample, with no FFT allocation per frame.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

BAND_COUNT = 4
DEFAULT_SAMPLE_RATE = 44_100
DEFAULT_EDGES = (150.0, 500.0, 2_000.0)


@dataclass(frozen=True, slots=True)
class Bands:
    """Overall level plus per-band RMS, both normalised to 0..1."""

    level: float
    values: tuple[float, ...]


def rms(samples: Sequence[float]) -> float:
    """Root mean square of normalised (-1..1) samples."""
    if not samples:
        return 0.0
    return math.sqrt(sum(x * x for x in samples) / len(samples))


def apply_envelope(
    current: float,
    target: float,
    dt: float,
    *,
    attack: float = 22.0,
    release: float = 7.0,
) -> float:
    """Frame-rate independent attack/release smoothing.

    ``attack`` and ``release`` are rates in 1/s: how fast the value chases a
    rising or falling target. Higher is snappier.
    """
    rate = attack if target > current else release
    alpha = 1.0 - math.exp(-rate * max(dt, 0.0))
    return current + (target - current) * alpha


def to_unit(value: float, *, gain: float = 4.0) -> float:
    """Map a raw RMS to 0..1 with a gentle knee, clamped."""
    return max(0.0, min(1.0, value * gain))


class _LowPass:
    """One-pole low-pass with persistent state across blocks."""

    __slots__ = ("_a", "_y")

    def __init__(self, sample_rate: float, cutoff: float) -> None:
        self._a = math.exp(-2.0 * math.pi * cutoff / sample_rate)
        self._y = 0.0

    def __call__(self, x: float) -> float:
        self._y = (1.0 - self._a) * x + self._a * self._y
        return self._y


class BandAnalyser:
    """Streaming 4-band split.

    Feed it consecutive blocks (typically 1024 samples at 44.1 kHz) and it keeps
    filter state, so band energy does not flicker at block boundaries.
    """

    __slots__ = ("_lows", "_sample_rate")

    def __init__(
        self,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        edges: Sequence[float] = DEFAULT_EDGES,
    ) -> None:
        if len(edges) != BAND_COUNT - 1:
            raise ValueError(f"expected {BAND_COUNT - 1} edge frequencies, got {len(edges)}")
        self._sample_rate = sample_rate
        self._lows = [_LowPass(sample_rate, f) for f in edges]

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    def process(self, samples: Sequence[float], *, gain: float = 4.0) -> Bands:
        if not samples:
            return Bands(level=0.0, values=(0.0,) * BAND_COUNT)

        low, mid_low, mid_high = self._lows
        energy = [0.0] * BAND_COUNT
        total = 0.0
        for x in samples:
            a = low(x)
            b = mid_low(x)
            c = mid_high(x)
            parts = (a, b - a, c - b, x - c)
            energy[0] += parts[0] * parts[0]
            energy[1] += parts[1] * parts[1]
            energy[2] += parts[2] * parts[2]
            energy[3] += parts[3] * parts[3]
            total += x * x

        n = len(samples)
        values = tuple(to_unit(math.sqrt(e / n), gain=gain) for e in energy)
        return Bands(level=to_unit(math.sqrt(total / n), gain=gain), values=values)

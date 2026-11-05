"""Tests for the synthetic source used by the UI until real capture lands."""

from __future__ import annotations

import pytest

from floatbeat.audio.demo import DemoSource


def _frames(count: int = 600, dt: float = 1 / 60) -> list[tuple[tuple[float, ...], float]]:
    source = DemoSource()
    return [source.read(dt) for _ in range(count)]


def test_output_is_deterministic() -> None:
    assert _frames(120) == _frames(120)


def test_values_stay_in_range() -> None:
    for bands, level in _frames():
        assert 0.0 <= level <= 1.0
        assert len(bands) == 4
        assert all(0.0 <= value <= 1.0 for value in bands)


def test_demo_has_a_pulse() -> None:
    levels = [level for _, level in _frames()]
    assert max(levels) > 0.6
    assert min(levels) < 0.6
    assert max(levels) - min(levels) > 0.15


def test_kick_hits_the_low_band() -> None:
    lows = [bands[0] for bands, _ in _frames()]
    assert max(lows) > 0.8
    assert sum(value > 0.7 for value in lows) > 5


def test_read_ignores_negative_dt() -> None:
    source = DemoSource()
    before = source.t
    source.read(-1.0)
    assert source.t == pytest.approx(before)

"""Tests for the audio analysis layer (no Qt required)."""

from __future__ import annotations

import math

import pytest

from floatbeat.audio.analysis import BandAnalyser, apply_envelope, rms, to_unit

SR = 44_100


def sine(freq: float, n: int = 8192, amp: float = 0.5, sr: int = SR) -> list[float]:
    return [amp * math.sin(2.0 * math.pi * freq * i / sr) for i in range(n)]


def test_rms_silence_is_zero() -> None:
    assert rms([0.0] * 128) == 0.0


def test_rms_of_sine() -> None:
    assert rms(sine(440.0, n=SR // 2)) == pytest.approx(0.5 / math.sqrt(2), abs=1e-3)


def test_empty_block_is_silent() -> None:
    bands = BandAnalyser().process([])
    assert bands.level == 0.0
    assert bands.values == (0.0, 0.0, 0.0, 0.0)


def test_low_tone_lands_in_low_band() -> None:
    bands = BandAnalyser().process(sine(100.0))
    assert bands.values[0] > bands.values[3]
    assert bands.values[0] > 0.1
    assert bands.level > 0.1


def test_high_tone_lands_in_high_band() -> None:
    bands = BandAnalyser().process(sine(6000.0))
    assert bands.values[3] > bands.values[0]
    assert bands.values[3] > 0.1


def test_louder_input_gives_higher_level() -> None:
    quiet = BandAnalyser().process(sine(440.0, amp=0.05))
    loud = BandAnalyser().process(sine(440.0, amp=0.6))
    assert loud.level > quiet.level


def test_analyser_keeps_state_across_blocks() -> None:
    analyser = BandAnalyser()
    block = sine(100.0, n=1024)
    first = analyser.process(block)
    second = analyser.process(block)
    assert first.values != (0.0, 0.0, 0.0, 0.0)
    assert second.values[0] == pytest.approx(first.values[0], rel=0.05)


def test_envelope_attacks_faster_than_it_releases() -> None:
    attack = apply_envelope(0.0, 1.0, 0.05, attack=22.0, release=7.0)
    release = apply_envelope(1.0, 0.0, 0.05, attack=22.0, release=7.0)
    assert attack > 0.5
    assert release > 0.6  # still high: falling is slower


def test_envelope_is_stable_for_zero_dt() -> None:
    assert apply_envelope(0.4, 0.9, 0.0) == 0.4


def test_to_unit_clamps() -> None:
    assert to_unit(-1.0) == 0.0
    assert to_unit(10.0) == 1.0
    assert to_unit(0.1) == pytest.approx(0.4)


def test_wrong_edge_count_is_rejected() -> None:
    with pytest.raises(ValueError):
        BandAnalyser(edges=(100.0,))

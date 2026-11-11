"""Tests for the MPRIS variant unwrapping (no session bus needed)."""

from __future__ import annotations

from floatbeat.audio.mpris import Track, unwrap


def test_unwrap_string_variant() -> None:
    assert unwrap(("s", "hello")) == "hello"


def test_unwrap_int64_variant() -> None:
    assert unwrap(("x", 42)) == 42


def test_unwrap_array_variant() -> None:
    assert unwrap(("as", ["a", "b"])) == ["a", "b"]


def test_unwrap_plain_value() -> None:
    assert unwrap(42) == 42
    assert unwrap("plain") == "plain"


def test_unwrap_dict_variant_keeps_inner_values() -> None:
    value = ("a{sv}", {"k": ("s", "v")})
    assert unwrap(value) == {"k": ("s", "v")}


def test_track_has_track() -> None:
    assert not Track().has_track
    assert Track(title="Song").has_track

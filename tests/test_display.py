"""Tests for window placement (pure geometry, no QApplication needed)."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QRect, QSize

from floatbeat.desktop.display import ANCHORS, anchor_position

AREA = QRect(0, 32, 1920, 1048)  # 1920x1080 with a 32 px top panel
SIZE = QSize(220, 220)
MARGIN = 24


def test_top_right_sits_under_the_panel() -> None:
    pos = anchor_position(AREA, SIZE, "top-right", MARGIN)
    assert pos.x() == 1920 - 220 - 24
    assert pos.y() == 32 + 24


def test_top_left() -> None:
    pos = anchor_position(AREA, SIZE, "top-left", MARGIN)
    assert (pos.x(), pos.y()) == (24, 56)


def test_bottom_right_uses_the_work_area_bottom() -> None:
    pos = anchor_position(AREA, SIZE, "bottom-right", MARGIN)
    assert pos.x() == 1920 - 220 - 24
    assert pos.y() == 32 + 1048 - 220 - 24


def test_bottom_left() -> None:
    pos = anchor_position(AREA, SIZE, "bottom-left", MARGIN)
    assert (pos.x(), pos.y()) == (24, 32 + 1048 - 220 - 24)


def test_all_declared_anchors_are_accepted() -> None:
    for anchor in ANCHORS:
        assert anchor_position(AREA, SIZE, anchor, MARGIN) is not None


def test_unknown_anchor_is_a_bug() -> None:
    with pytest.raises(ValueError):
        anchor_position(AREA, SIZE, "middle", MARGIN)


def test_secondary_screen_offset_is_respected() -> None:
    area = QRect(1920, 32, 1280, 992)
    pos = anchor_position(area, SIZE, "top-right", MARGIN)
    assert (pos.x(), pos.y()) == (1920 + 1280 - 220 - 24, 56)

"""Desktop integration helpers."""

from .display import (
    ANCHORS,
    DEFAULT_ANCHOR,
    DEFAULT_MARGIN,
    anchor_position,
    default_position,
    prefer_xwayland,
    restore_window_position,
)

__all__ = [
    "ANCHORS",
    "DEFAULT_ANCHOR",
    "DEFAULT_MARGIN",
    "anchor_position",
    "default_position",
    "prefer_xwayland",
    "restore_window_position",
]

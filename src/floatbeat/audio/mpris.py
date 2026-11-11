"""MPRIS2 client built on jeepney.

PySide6's QtDBus cannot demarshal the ``a{sv}`` metadata dictionary (the
``QDBusArgument`` copy loses its state), so the player metadata is read through
jeepney, a pure-Python D-Bus library. QtDBus is still used for our own outgoing
service in :mod:`floatbeat.engine`.

The client is blocking on purpose: it runs in the engine's main thread and every
call is a small local round-trip. Metadata is refreshed twice per second, which
is cheap and keeps the implementation dependency-free.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from jeepney import DBusAddress, new_method_call
from jeepney.bus_messages import message_bus
from jeepney.io.blocking import open_dbus_connection

MPRIS_PREFIX = "org.mpris.MediaPlayer2."
PLAYER_PATH = "/org/mpris/MediaPlayer2"
PLAYER_IFACE = "org.mpris.MediaPlayer2.Player"
PROPS_IFACE = "org.freedesktop.DBus.Properties"

_TYPE_CODES = set("ybnqiuxtdsogavh")


def unwrap(value):
    """Unwrap jeepney's ``(signature, value)`` variant tuples recursively."""
    while (
        isinstance(value, tuple)
        and len(value) == 2
        and isinstance(value[0], str)
        and value[0]
        and value[0][0] in _TYPE_CODES
    ):
        value = value[1]
    return value


@dataclass
class Track:
    title: str = ""
    artist: str = ""
    album: str = ""
    art_url: str = ""
    length_us: int = 0
    position_us: int = 0
    playing: bool = False
    can_next: bool = True
    can_previous: bool = True
    service: str = ""

    @property
    def has_track(self) -> bool:
        return bool(self.title)


@dataclass
class MprisClient:
    connection: object | None = None
    track: Track = field(default_factory=Track)

    def __post_init__(self) -> None:
        try:
            self.connection = open_dbus_connection(bus="SESSION")
        except Exception:
            self.connection = None

    # -- discovery ----------------------------------------------------------

    def _player_names(self) -> list[str]:
        if self.connection is None:
            return []
        try:
            reply = self.connection.send_and_get_reply(message_bus.ListNames())
            return sorted(name for name in reply.body[0] if name.startswith(MPRIS_PREFIX))
        except Exception:
            return []

    def _props(self, service: str) -> dict:
        if self.connection is None:
            return {}
        address = DBusAddress(PLAYER_PATH, bus_name=service, interface=PROPS_IFACE)
        message = new_method_call(address, "GetAll", "s", (PLAYER_IFACE,))
        try:
            reply = self.connection.send_and_get_reply(message)
            return unwrap(reply.body[0]) if reply.body else {}
        except Exception:
            return {}

    def _pick(self, names: list[str]) -> str:
        """Prefer the player that is actually playing, else the first one."""
        fallback = ""
        for name in names:
            props = self._props(name)
            if props.get("PlaybackStatus") == "Playing":
                return name
            if not fallback:
                fallback = name
        return fallback

    # -- public API ---------------------------------------------------------

    def refresh(self) -> Track:
        names = self._player_names()
        if not names:
            self.track = Track()
            return self.track

        service = self.track.service
        if service not in names:
            service = self._pick(names)

        props = self._props(service)
        if not props:
            self.track = Track()
            return self.track

        metadata: dict = unwrap(props.get("Metadata", {}))
        title = str(unwrap(metadata.get("xesam:title", "")) or "")
        artist_raw = unwrap(metadata.get("xesam:artist", [])) or []
        if isinstance(artist_raw, str):
            artist = artist_raw
        else:
            artist = ", ".join(str(a) for a in artist_raw)

        self.track = Track(
            title=title,
            artist=artist,
            album=str(unwrap(metadata.get("xesam:album", "")) or ""),
            art_url=str(unwrap(metadata.get("mpris:artUrl", "")) or ""),
            length_us=int(unwrap(metadata.get("mpris:length", 0)) or 0),
            position_us=int(unwrap(props.get("Position", 0)) or 0),
            playing=props.get("PlaybackStatus") == "Playing",
            can_next=bool(unwrap(props.get("CanGoNext", True))),
            can_previous=bool(unwrap(props.get("CanGoPrevious", True))),
            service=service,
        )
        return self.track

    def _player_address(self):
        return DBusAddress(PLAYER_PATH, bus_name=self.track.service, interface=PLAYER_IFACE)

    def _call(self, method: str) -> None:
        if self.connection is None or not self.track.service:
            return
        try:
            message = new_method_call(self._player_address(), method)
            self.connection.send_and_get_reply(message)
        except Exception:
            pass

    def play_pause(self) -> None:
        self._call("PlayPause")

    def next(self) -> None:
        if self.track.can_next:
            self._call("Next")

    def previous(self) -> None:
        if self.track.can_previous:
            self._call("Previous")

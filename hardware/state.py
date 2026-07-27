"""
Compatibility state adapter — mirrors the original PlayerState API by
delegating to the new functional hardware modules via ``__getattr__`` /
``__setattr__``.

New code should import directly from the hardware modules (e.g.
``hardware.battery.get_battery_percent()``) rather than using this class.
This adapter exists so existing screens and menu code can continue to
work without a full rewrite.
"""

from typing import Any


# ── mapping: attribute -> (module, getter, setter) ──────────────────────────
#
# Every attribute the old code accessed on PlayerState is mapped to its
# getter/setter in the new functional API.  Add new entries here when you
# port an attribute; remove entries when no code references them any more.

_HW_MAP = {
    # battery
    "battery_percent":       ("battery",   "get_battery_percent",   "set_battery_percent"),
    "charging":              ("battery",   "is_charging",           "set_charging"),
    "charged_full":          ("battery",   "is_charged_full",       "set_charged_full"),
    # input
    "hold_active":           ("input",     "is_hold_active",        "set_hold_active"),
    "remote_hold_active":    ("input",     "is_remote_hold_active", "set_remote_hold_active"),
    # disk
    "disk_active":           ("disk",      "is_disk_active",        "set_disk_active"),
    # audio
    "play_state":            ("audio",     "get_play_state",        "set_play_state"),
    "elapsed_sec":           ("audio",     "get_elapsed_sec",       "set_elapsed_sec"),
    "track_length_sec":      ("audio",     "get_track_length_sec",  "set_track_length_sec"),
    "playlist_pos":          ("audio",     "get_playlist_pos",      "set_playlist_pos"),
    "playlist_len":          ("audio",     "get_playlist_len",      None),
    "title":                 ("audio",     "get_title",             "set_title"),
    "artist":                ("audio",     "get_artist",            "set_artist"),
    "album":                 ("audio",     "get_album",             "set_album"),
    "filename":              ("audio",     "get_filename",          None),
    "bitrate_kbps":          ("audio",     "get_bitrate_kbps",      None),
    "samplerate_hz":         ("audio",     "get_samplerate_hz",     None),
    "is_vbr":                ("audio",     "is_vbr",                None),
    "has_id3":               ("audio",     "has_id3",               None),
    "next_title":            ("audio",     "get_next_title",        None),
    "album_art_path":        ("audio",     "get_album_art_path",    "set_album_art_path"),
    # volume
    "volume_percent":        ("volume",    "get_volume_percent",    "set_volume_percent"),
    "volume_change_timer":   ("volume",    "_get_change_timer",     "_set_change_timer"),
    "volume_limit":          ("volume",    "get_volume_limit",      "set_volume_limit"),
    # display
    "backlight_timeout_s":   ("display",   "get_backlight_timeout", "set_backlight_timeout"),
    "backlight_mode":        ("display",   "get_backlight_mode",    "set_backlight_mode"),
    "contrast":              ("display",   "get_contrast",          "set_contrast"),
    # storage / about
    "model_name":            ("storage",   "get_model_name",        None),
    "firmware_version":      ("storage",   "get_firmware_version",  None),
    "serial_number":         ("storage",   "get_serial_number",     None),
    "storage_capacity_gb":   ("storage",   "get_capacity_gb",       None),
    "storage_free_gb":       ("storage",   "get_free_gb",           "set_free_gb"),
    "song_count":            ("storage",   "get_song_count",        None),
    # settings
    "shuffle_enabled":       ("settings",  "is_shuffle_enabled",    "set_shuffle_enabled"),
    "repeat_mode":           ("settings",  "get_repeat_mode",       "set_repeat_mode"),
    "clicker_enabled":       ("settings",  "is_clicker_enabled",    "set_clicker_enabled"),
    "language":              ("settings",  "get_language",          "set_language"),
    "sound_check":           ("settings",  "is_sound_check_enabled","set_sound_check_enabled"),
    # clock
    "clock_24h":             ("clock",     "is_24h",                "set_24h"),
    "hour":                  ("clock",     "get_hour",              None),
    "minute":                ("clock",     "get_minute",            None),
    "day":                   ("clock",     "_get_day",              None),
    "month":                 ("clock",     "_get_month",            None),
    "year":                  ("clock",     "_get_year",             None),
}

_MOD_CACHE: dict[str, Any] = {}


def _get_mod(name: str):
    if name not in _MOD_CACHE:
        import importlib
        _MOD_CACHE[name] = importlib.import_module(f".{name}", __package__)
    return _MOD_CACHE[name]


class PlayerState:
    """**DEPRECATED** — prefer importing from the individual hardware modules.

    Proxies attribute access to the functional hardware API via _HW_MAP.
    Attributes not in the map are stored as plain instance attributes
    (for transient state like ``browse_current_path``).
    """

    def __init__(self):
        self._transient: dict[str, Any] = {}
        self._transient["browse_current_path"] = "/"

    # ---- computed properties ----------------------------------------------

    @property
    def track_progress(self) -> float:
        from .audio import get_track_length_sec, get_elapsed_sec
        length = get_track_length_sec()
        if length <= 0:
            return 0.0
        return min(1.0, get_elapsed_sec() / length)

    @property
    def remaining_sec(self) -> float:
        from .audio import get_track_length_sec, get_elapsed_sec
        return max(0.0, get_track_length_sec() - get_elapsed_sec())

    @property
    def near_end(self) -> bool:
        return self.remaining_sec < 10

    @property
    def volume_mode_active(self) -> bool:
        from .volume import _get_change_timer
        return _get_change_timer() > 0

    @property
    def audio_active(self) -> bool:
        from .audio import get_play_state
        return get_play_state() in ("PLAYING", "PAUSED")

    # ---- generic proxy ----------------------------------------------------

    def __getattr__(self, name: str) -> Any:
        if "_transient" in self.__dict__ and name in self.__dict__["_transient"]:
            return self.__dict__["_transient"][name]
        entry = _HW_MAP.get(name)
        if entry:
            mod_name, getter, _ = entry
            if not getter:
                raise AttributeError(f"PlayerState.{name} has no getter")
            mod = _get_mod(mod_name)
            return getattr(mod, getter)()
        raise AttributeError(f"PlayerState has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        if name in ("_transient",):
            object.__setattr__(self, name, value)
            return
        entry = _HW_MAP.get(name)
        if entry:
            mod_name, _, setter = entry
            if setter:
                mod = _get_mod(mod_name)
                getattr(mod, setter)(value)
                return
            raise AttributeError(f"PlayerState.{name} is read-only (no setter)")
        if name.startswith("_"):
            object.__setattr__(self, name, value)
        else:
            self._transient[name] = value


def update_stub_state(state: PlayerState, dt: float) -> None:
    """Global stub-tick — calls tick_stub on every hardware module."""
    from .battery import tick_stub as tb
    from .clock import tick_stub as tc
    from .disk import tick_stub as td
    from .audio import tick_stub as ta
    from .display import tick_stub as tdsp
    from .storage import tick_stub as ts
    from .volume import tick_stub as tv
    from .settings import tick_stub as tset
    from .input import tick_stub as ti
    tb(dt); tc(dt); td(dt); ta(dt); tdsp(dt)
    ts(dt); tv(dt); tset(dt); ti(dt)
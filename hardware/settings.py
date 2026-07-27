"""
Miscellaneous settings that don't fit neatly into other hardware modules.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class _SettingsStub:
    shuffle_enabled: bool = False
    repeat_mode: str = "OFF"       # OFF | ALL | ONE | AB | SHUFFLE
    clicker_enabled: bool = True
    language: str = "English"
    sound_check: bool = False


_IMPL = _SettingsStub()


# ---- public API ------------------------------------------------------------

def is_shuffle_enabled() -> bool:
    return _IMPL.shuffle_enabled


def set_shuffle_enabled(enabled: bool) -> None:
    _IMPL.shuffle_enabled = enabled


def get_repeat_mode() -> str:
    return _IMPL.repeat_mode


def set_repeat_mode(mode: str) -> None:
    assert mode in ("OFF", "ALL", "ONE", "AB", "SHUFFLE"), f"Invalid repeat mode: {mode}"
    _IMPL.repeat_mode = mode


def is_clicker_enabled() -> bool:
    return _IMPL.clicker_enabled


def set_clicker_enabled(enabled: bool) -> None:
    _IMPL.clicker_enabled = enabled


def get_language() -> str:
    return _IMPL.language


def set_language(lang: str) -> None:
    _IMPL.language = lang


def is_sound_check_enabled() -> bool:
    return _IMPL.sound_check


def set_sound_check_enabled(enabled: bool) -> None:
    _IMPL.sound_check = enabled


def reset_all_settings() -> None:
    """Factory-default all settings."""
    _IMPL.shuffle_enabled = False
    _IMPL.repeat_mode = "OFF"
    _IMPL.clicker_enabled = True
    _IMPL.language = "English"
    _IMPL.sound_check = False
    # Also reset hardware modules that have settings
    from . import display, volume
    display.set_backlight_mode("ON")
    display.set_backlight_timeout(10)
    display.set_contrast(50)
    volume.set_volume_limit(100)


def tick_stub(dt: float) -> None:
    pass
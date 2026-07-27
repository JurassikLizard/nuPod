"""
Display / backlight / contrast hardware interface.
"""

from dataclasses import dataclass


@dataclass
class _DisplayStub:
    backlight_mode: str = "ON"     # ON | OFF
    backlight_timeout_s: int = 10
    contrast: int = 50


_IMPL = _DisplayStub()


# ---- public API ------------------------------------------------------------

def get_backlight_mode() -> str:
    return _IMPL.backlight_mode


def set_backlight_mode(mode: str) -> None:
    assert mode in ("ON", "OFF"), f"Invalid backlight mode: {mode}"
    _IMPL.backlight_mode = mode


def get_backlight_timeout() -> int:
    return _IMPL.backlight_timeout_s


def set_backlight_timeout(seconds: int) -> None:
    _IMPL.backlight_timeout_s = max(0, seconds)


def get_contrast() -> int:
    return _IMPL.contrast


def set_contrast(val: int) -> None:
    _IMPL.contrast = max(0, min(100, val))


def tick_stub(dt: float) -> None:
    pass
"""
Hold-switch / physical-input hardware interface.
"""

from dataclasses import dataclass


@dataclass
class _InputStub:
    hold_active: bool = False
    remote_hold_active: bool = False


_IMPL = _InputStub()


# ---- public API ------------------------------------------------------------

def is_hold_active() -> bool:
    return _IMPL.hold_active


def set_hold_active(v: bool) -> None:
    _IMPL.hold_active = v


def is_remote_hold_active() -> bool:
    return _IMPL.remote_hold_active


def set_remote_hold_active(v: bool) -> None:
    _IMPL.remote_hold_active = v


def tick_stub(dt: float) -> None:
    pass
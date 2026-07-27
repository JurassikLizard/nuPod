"""
Volume hardware interface.
"""

from dataclasses import dataclass


@dataclass
class _VolumeStub:
    percent: float = 60.0
    limit: int = 100
    change_timer: float = 0.0  # >0 => show volume bar instead of progress bar


_IMPL = _VolumeStub()


# ---- public API ------------------------------------------------------------

def get_volume_percent() -> float:
    return _IMPL.percent


def set_volume_percent(pct: float) -> None:
    _IMPL.percent = max(0.0, min(float(_IMPL.limit), pct))


def get_volume_limit() -> int:
    return _IMPL.limit


def set_volume_limit(limit: int) -> None:
    _IMPL.limit = max(0, min(100, limit))
    _IMPL.percent = min(_IMPL.percent, float(_IMPL.limit))


def is_volume_mode_active() -> bool:
    """Return True when the volume-change-timer is running (show volume bar)."""
    return _IMPL.change_timer > 0


def trigger_volume_change() -> None:
    """Start the volume-change display timer."""
    _IMPL.change_timer = 1.5


def _get_change_timer() -> float:
    """Internal — used by PlayerState adapter."""
    return _IMPL.change_timer


def _set_change_timer(v: float) -> None:
    """Internal — used by PlayerState adapter."""
    _IMPL.change_timer = max(0.0, v)


def tick_stub(dt: float) -> None:
    _IMPL.change_timer = max(0.0, _IMPL.change_timer - dt)
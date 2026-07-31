"""
Volume hardware interface.

Controls both the in-app volume level and the system output volume
via PulseAudio (``pactl``) so changes take effect in real-time.
"""

import subprocess
from dataclasses import dataclass


@dataclass
class _VolumeStub:
    percent: float = 60.0
    limit: int = 100
    change_timer: float = 0.0  # >0 => show volume bar instead of progress bar


_IMPL = _VolumeStub()


def _apply_system_volume(pct: float) -> None:
    """Set the system audio sink volume to *pct* (0-100)."""
    try:
        subprocess.run(
            ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{int(pct)}%"],
            capture_output=True, timeout=5,
        )
    except Exception:
        pass  # no PulseAudio — just track the value


# ---- public API ------------------------------------------------------------

def get_volume_percent() -> float:
    return _IMPL.percent


def set_volume_percent(pct: float) -> None:
    _IMPL.percent = max(0.0, min(float(_IMPL.limit), pct))
    _apply_system_volume(_IMPL.percent)


def get_volume_limit() -> int:
    return _IMPL.limit


def set_volume_limit(limit: int) -> None:
    _IMPL.limit = max(0, min(100, limit))
    _IMPL.percent = min(_IMPL.percent, float(_IMPL.limit))


def is_volume_mode_active() -> bool:
    """Return True when the volume-change-timer is running (show volume bar)."""
    return _IMPL.change_timer > 0


def trigger_volume_change() -> None:
    """Start the volume-change display timer (3-second auto-hide)."""
    _IMPL.change_timer = 3.0


def clear_volume_mode() -> None:
    """Immediately hide the volume bar."""
    _IMPL.change_timer = 0.0


def _get_change_timer() -> float:
    """Internal — volume-change display timer."""
    return _IMPL.change_timer


def _set_change_timer(v: float) -> None:
    """Internal — volume-change display timer."""
    _IMPL.change_timer = max(0.0, v)


def tick_stub(dt: float) -> None:
    _IMPL.change_timer = max(0.0, _IMPL.change_timer - dt)
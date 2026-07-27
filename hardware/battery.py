"""
Battery hardware interface.

Provides functions to read battery status. Currently stub-based;
swap the ``_IMPL`` object for a real hardware driver.
"""

from dataclasses import dataclass


@dataclass
class _BatteryStub:
    percent: float = 80.0
    charging: bool = False
    charged_full: bool = False


_IMPL = _BatteryStub()


# ---- public API ------------------------------------------------------------

def get_battery_percent() -> float:
    """Return battery charge 0..100."""
    return _IMPL.percent


def is_charging() -> bool:
    """Return True if the device is plugged in and charging."""
    return _IMPL.charging


def is_charged_full() -> bool:
    """Return True if the battery is fully charged (charger still attached)."""
    return _IMPL.charged_full


def set_battery_percent(pct: float) -> None:
    """Override battery level (stub support)."""
    _IMPL.percent = max(0.0, min(100.0, pct))


def set_charging(charging: bool) -> None:
    """Set charging state (stub support)."""
    _IMPL.charging = charging
    if charging:
        _IMPL.charged_full = False


def set_charged_full(full: bool) -> None:
    """Set charged-full state (stub support)."""
    _IMPL.charged_full = full
    if full:
        _IMPL.charging = True


def tick_stub(dt: float) -> None:
    """Advance stub simulation for one frame."""
    # Battery drains slowly during playback
    if _IMPL.charging:
        _IMPL.percent = min(100.0, _IMPL.percent + 2.0 * dt)
        if _IMPL.percent >= 100.0:
            _IMPL.charged_full = True
            _IMPL.charging = False
    elif _IMPL.percent > 0:
        _IMPL.percent = max(0.0, _IMPL.percent - 0.1 * dt)
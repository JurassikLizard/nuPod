"""
Clock / RTC hardware interface.
"""

from dataclasses import dataclass


@dataclass
class _ClockStub:
    hour: int = 12
    minute: int = 0
    second: float = 0.0
    day: int = 27
    month: int = 7
    year: int = 2026
    mode_24h: bool = True


_IMPL = _ClockStub()


# ---- public API ------------------------------------------------------------

def get_hour() -> int:
    return _IMPL.hour


def get_minute() -> int:
    return _IMPL.minute


def get_second() -> float:
    return _IMPL.second


def get_date() -> tuple:
    """Return (day, month, year)."""
    return _IMPL.day, _IMPL.month, _IMPL.year


def is_24h() -> bool:
    return _IMPL.mode_24h


def set_24h(enabled: bool) -> None:
    _IMPL.mode_24h = enabled


def set_datetime(hour: int, minute: int, second: float,
                 day: int, month: int, year: int) -> None:
    _IMPL.hour = hour % 24
    _IMPL.minute = minute % 60
    _IMPL.second = second % 60.0
    _IMPL.day = day
    _IMPL.month = month
    _IMPL.year = year


def format_time() -> str:
    """Return a formatted time string respecting 12/24h setting."""
    h = _IMPL.hour
    m = _IMPL.minute
    if _IMPL.mode_24h:
        return f"{h:02d}:{m:02d}"
    h12 = h % 12 or 12
    ampm = "AM" if h < 12 else "PM"
    return f"{h12}:{m:02d} {ampm}"


def format_date() -> str:
    """Return a formatted date string."""
    months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    month_name = months[_IMPL.month] if 1 <= _IMPL.month <= 12 else "???"
    return f"{month_name} {_IMPL.day}, {_IMPL.year}"


def _get_day() -> int:
    return _IMPL.day


def _get_month() -> int:
    return _IMPL.month


def _get_year() -> int:
    return _IMPL.year


def tick_stub(dt: float) -> None:
    """Advance stub time (sped up for demo visibility)."""
    _IMPL.second += dt * 10.0  # 10x speed for demo
    if _IMPL.second >= 60.0:
        _IMPL.second -= 60.0
        _IMPL.minute += 1
        if _IMPL.minute >= 60:
            _IMPL.minute = 0
            _IMPL.hour = (_IMPL.hour + 1) % 24
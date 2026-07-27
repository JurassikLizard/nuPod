"""
Storage / filesystem hardware interface.
"""

from dataclasses import dataclass


@dataclass
class _StorageStub:
    capacity_gb: int = 160
    free_gb: int = 80
    song_count: int = 4123
    model_name: str = "iPod Classic"
    firmware_version: str = "1.5.0"
    serial_number: str = "A1234567890"


_IMPL = _StorageStub()


# ---- public API ------------------------------------------------------------

def get_capacity_gb() -> int:
    return _IMPL.capacity_gb


def get_free_gb() -> int:
    return _IMPL.free_gb


def set_free_gb(gb: int) -> None:
    _IMPL.free_gb = max(0, gb)


def get_song_count() -> int:
    return _IMPL.song_count


def get_model_name() -> str:
    return _IMPL.model_name


def get_firmware_version() -> str:
    return _IMPL.firmware_version


def get_serial_number() -> str:
    return _IMPL.serial_number


def tick_stub(dt: float) -> None:
    pass
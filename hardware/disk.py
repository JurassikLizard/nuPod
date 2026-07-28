"""
Disk-activity (spinning / flash-access) hardware interface.
"""

from dataclasses import dataclass


@dataclass
class _DiskStub:
    active: bool = False
    _blip_timer: float = 0.0


_IMPL = _DiskStub()


# ---- public API ------------------------------------------------------------

def is_disk_active() -> bool:
    """Return True when the disk / flash is being accessed."""
    return _IMPL.active


def set_disk_active(v: bool) -> None:
    _IMPL.active = v


def tick_stub(dt: float) -> None:
    """Disk activity is only triggered by actual operations (library scan, etc.)."""
    pass
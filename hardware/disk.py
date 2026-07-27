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
    """Brief periodic disk-access blip to exercise the animation."""
    _IMPL._blip_timer += dt
    if _IMPL._blip_timer >= 1.0:
        _IMPL._blip_timer = 0.0
        _IMPL.active = not _IMPL.active
"""
Audio playback hardware interface.

Uses python-mpv (libmpv) for playback, giving us real-time volume control,
instant seeking, proper pause/resume, and event-driven track-end detection.
"""

import atexit
import os
from dataclasses import dataclass, field
from typing import Optional

import mpv


# ── Internal state ───────────────────────────────────────────────────────────

@dataclass
class _AudioState:
    play_state: str = "STOPPED"       # STOPPED | PLAYING | PAUSED
    title: str = ""
    artist: str = ""
    album: str = ""
    filename: str = ""
    album_art_path: Optional[str] = None
    elapsed_sec: float = 0.0
    track_length_sec: float = 0.0
    queue: list = field(default_factory=list)
    queue_pos: int = 0
    local_mode: bool = False
    _pending_next: bool = False  # set True when end-file fires


_IMPL = _AudioState()

# Single mpv player instance for the whole app lifecycle
_player: Optional[mpv.MPV] = None


def _get_player() -> mpv.MPV:
    """Lazy-init the mpv player singleton."""
    global _player
    if _player is None:
        _player = mpv.MPV(ytdl=False)
        _player.volume = 60  # default
        # Track end → signal next_track to fire on the main thread
        _player.register_event_callback(_on_mpv_event)
        atexit.register(_cleanup)
    return _player


def _cleanup() -> None:
    """Terminate mpv on exit."""
    global _player
    if _player is not None:
        try:
            _player.terminate()
        except Exception:
            pass
        _player = None


def _on_mpv_event(event) -> None:
    """Called from mpv's thread when an event fires."""
    if event.event_id == mpv.MpvEventID.END_FILE:
        _IMPL._pending_next = True


# ── Public API ───────────────────────────────────────────────────────────────

def get_play_state() -> str:
    return _IMPL.play_state


def set_play_state(state: str) -> None:
    assert state in ("STOPPED", "PLAYING", "PAUSED"), f"Invalid state: {state}"
    player = _get_player()
    if state == "STOPPED":
        player.stop()
        _IMPL.play_state = "STOPPED"
        _IMPL.elapsed_sec = 0.0
    elif state == "PAUSED":
        player.pause = True
        _IMPL.play_state = "PAUSED"
        _IMPL.elapsed_sec = get_current_time()
    elif state == "PLAYING":
        player.pause = False
        _IMPL.play_state = "PLAYING"
        _IMPL.elapsed_sec = get_current_time()


def get_current_time() -> float:
    """Current playback position in seconds (from mpv)."""
    if _player is not None:
        try:
            pos = _player.time_pos
            if pos is not None:
                return float(pos)
        except Exception:
            pass
    return _IMPL.elapsed_sec


def get_elapsed_sec() -> float:
    return get_current_time()


def set_elapsed_sec(sec: float) -> None:
    _IMPL.elapsed_sec = max(0.0, sec)


def seek_to(sec: float) -> None:
    """Seek to a specific position in the current track."""
    _IMPL.elapsed_sec = max(0.0, sec)
    if _player is not None:
        try:
            _player.time_pos = _IMPL.elapsed_sec
        except Exception:
            pass


def get_track_length_sec() -> float:
    """Track duration from mpv if available, else stored value."""
    if _player is not None:
        try:
            dur = _player.duration
            if dur is not None and dur > 0:
                return float(dur)
        except Exception:
            pass
    return _IMPL.track_length_sec


def set_track_length_sec(sec: float) -> None:
    _IMPL.track_length_sec = max(0.0, sec)


def get_track_progress() -> float:
    length = get_track_length_sec()
    if length <= 0:
        return 0.0
    return min(1.0, get_current_time() / length)


def get_remaining_sec() -> float:
    return max(0.0, get_track_length_sec() - get_current_time())


def is_near_end() -> bool:
    return get_remaining_sec() < 10


def is_audio_active() -> bool:
    return _IMPL.play_state in ("PLAYING", "PAUSED")


def set_volume(pct: float) -> None:
    """Set playback volume (0-100) in real time."""
    if _player is not None:
        try:
            _player.volume = max(0, min(100, int(pct)))
        except Exception:
            pass


def get_title() -> str:
    return _IMPL.title


def set_title(title: str) -> None:
    _IMPL.title = title


def get_artist() -> str:
    return _IMPL.artist


def set_artist(artist: str) -> None:
    _IMPL.artist = artist


def get_album() -> str:
    return _IMPL.album


def set_album(album: str) -> None:
    _IMPL.album = album


def get_filename() -> str:
    return _IMPL.filename


def get_album_art_path() -> Optional[str]:
    return _IMPL.album_art_path


def set_album_art_path(path: Optional[str]) -> None:
    _IMPL.album_art_path = path


def get_current_filepath() -> Optional[str]:
    if _IMPL.queue and 0 <= _IMPL.queue_pos < len(_IMPL.queue):
        return _IMPL.queue[_IMPL.queue_pos].get("filepath")
    return None


# ── Queue API ────────────────────────────────────────────────────────────────

def is_local() -> bool:
    return _IMPL.local_mode


def set_local(v: bool) -> None:
    _IMPL.local_mode = v


def get_queue_len() -> int:
    return len(_IMPL.queue)


def get_queue_pos() -> int:
    return _IMPL.queue_pos


def set_queue_pos(pos: int) -> None:
    _IMPL.queue_pos = max(0, min(len(_IMPL.queue) - 1, pos)) if _IMPL.queue else 0


def get_queue() -> list:
    return list(_IMPL.queue)


def set_queue(songs: list) -> None:
    _IMPL.queue = list(songs)
    _IMPL.queue_pos = 0
    _IMPL.local_mode = True


def _apply_metadata(song: dict) -> None:
    _IMPL.title = song.get("title", "Unknown")
    _IMPL.artist = song.get("artist", "Unknown Artist")
    _IMPL.album = song.get("album", "Unknown Album")
    _IMPL.filename = os.path.basename(song.get("filepath", ""))
    _IMPL.album_art_path = song.get("cover_art_path")
    _IMPL.track_length_sec = float(song.get("duration_sec", 0))
    _IMPL.elapsed_sec = 0.0


def play_current() -> None:
    """Start playback of the current queue item."""
    if not _IMPL.queue or _IMPL.queue_pos >= len(_IMPL.queue):
        _IMPL.play_state = "STOPPED"
        return

    song = _IMPL.queue[_IMPL.queue_pos]
    _apply_metadata(song)

    player = _get_player()
    fp = song.get("filepath", "")
    if os.path.exists(fp):
        player.play(fp)
    player.pause = False
    _IMPL.play_state = "PLAYING"
    _IMPL.elapsed_sec = 0.0
    _IMPL._pending_next = False

    # Sync volume
    try:
        from hardware.volume import get_volume_percent
        set_volume(get_volume_percent())
    except Exception:
        pass


def next_track() -> bool:
    """Advance to the next track. Returns True if there was a next track."""
    if not _IMPL.queue:
        return False

    from hardware import settings

    repeat = settings.get_repeat_mode()
    if repeat == "ONE":
        play_current()
        return True

    next_pos = _IMPL.queue_pos + 1
    if next_pos >= len(_IMPL.queue):
        if repeat == "ALL":
            next_pos = 0
        elif repeat == "SHUFFLE":
            import random
            next_pos = random.randrange(len(_IMPL.queue))
        else:
            # OFF — stop at end
            _get_player().stop()
            _IMPL.play_state = "STOPPED"
            _IMPL.elapsed_sec = 0.0
            return False

    _IMPL.queue_pos = next_pos
    play_current()
    return True


def prev_track() -> bool:
    """Go to the previous track (or restart current if >3s elapsed)."""
    if not _IMPL.queue:
        return False

    if get_current_time() > 3.0:
        seek_to(0.0)
        return True

    prev_pos = _IMPL.queue_pos - 1
    if prev_pos < 0:
        prev_pos = 0
    _IMPL.queue_pos = prev_pos
    play_current()
    return True


def stop() -> None:
    """Stop playback."""
    _get_player().stop()
    _IMPL.play_state = "STOPPED"
    _IMPL.elapsed_sec = 0.0


# ── Tick ─────────────────────────────────────────────────────────────────────

def tick_stub(dt: float) -> None:
    """Called every frame. Checks for track-end and auto-advances."""
    if _IMPL._pending_next and _IMPL.play_state == "PLAYING":
        _IMPL._pending_next = False
        next_track()

    # Update elapsed from mpv so the UI stays in sync
    if _IMPL.play_state == "PLAYING":
        _IMPL.elapsed_sec = get_current_time()
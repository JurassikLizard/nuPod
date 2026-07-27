"""
Audio playback hardware interface.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class _AudioStub:
    play_state: str = "PLAYING"          # STOPPED | PLAYING | PAUSED | FF | REW
    elapsed_sec: float = 0.0
    track_length_sec: float = 210.0
    playlist_pos: int = 1
    playlist_len: int = 12
    title: str = "Sample Track"
    artist: str = "Sample Artist"
    album: str = "Sample Album"
    filename: str = "sample.mp3"
    bitrate_kbps: int = 320
    samplerate_hz: int = 44100
    is_vbr: bool = False
    has_id3: bool = True
    next_title: Optional[str] = "Next Track"
    album_art_path: Optional[str] = None


_IMPL = _AudioStub()


# ---- public API ------------------------------------------------------------

def get_play_state() -> str:
    return _IMPL.play_state


def set_play_state(state: str) -> None:
    assert state in ("STOPPED", "PLAYING", "PAUSED", "FF", "REW"), f"Invalid state: {state}"
    _IMPL.play_state = state


def get_elapsed_sec() -> float:
    return _IMPL.elapsed_sec


def get_track_length_sec() -> float:
    return _IMPL.track_length_sec


def get_track_progress() -> float:
    if _IMPL.track_length_sec <= 0:
        return 0.0
    return min(1.0, _IMPL.elapsed_sec / _IMPL.track_length_sec)


def get_remaining_sec() -> float:
    return max(0.0, _IMPL.track_length_sec - _IMPL.elapsed_sec)


def is_near_end() -> bool:
    return get_remaining_sec() < 10


def is_audio_active() -> bool:
    return _IMPL.play_state in ("PLAYING", "PAUSED")


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


def get_bitrate_kbps() -> int:
    return _IMPL.bitrate_kbps


def get_samplerate_hz() -> int:
    return _IMPL.samplerate_hz


def is_vbr() -> bool:
    return _IMPL.is_vbr


def has_id3() -> bool:
    return _IMPL.has_id3


def get_next_title() -> Optional[str]:
    return _IMPL.next_title


def get_album_art_path() -> Optional[str]:
    return _IMPL.album_art_path


def set_album_art_path(path: Optional[str]) -> None:
    _IMPL.album_art_path = path


def get_playlist_pos() -> int:
    return _IMPL.playlist_pos


def set_playlist_pos(pos: int) -> None:
    _IMPL.playlist_pos = pos


def get_playlist_len() -> int:
    return _IMPL.playlist_len


def set_playlist_len(length: int) -> None:
    _IMPL.playlist_len = length


def set_elapsed_sec(sec: float) -> None:
    _IMPL.elapsed_sec = max(0.0, sec)


def set_track_length_sec(sec: float) -> None:
    _IMPL.track_length_sec = max(0.0, sec)


def play_file(title: str, artist: str = "Unknown Artist",
              album: str = "Unknown Album") -> None:
    """Start playback of a track, updating metadata."""
    _IMPL.title = title
    _IMPL.artist = artist
    _IMPL.album = album
    _IMPL.elapsed_sec = 0.0
    _IMPL.play_state = "PLAYING"


def tick_stub(dt: float) -> None:
    if _IMPL.play_state == "PLAYING":
        _IMPL.elapsed_sec += dt
        if _IMPL.elapsed_sec >= _IMPL.track_length_sec:
            _IMPL.elapsed_sec = 0.0
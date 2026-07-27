"""
Music player — wraps pydub for audio playback and provides
play/pause/stop/seek controls.

This module is designed to eventually be driven by the hardware
abstraction layer (``hardware/audio.py``) but can also be used
standalone for testing.

State machine::

    STOPPED ──play()──► PLAYING ──pause()──► PAUSED
      ▲                   │                    │
      └───stop()──────────┴───stop()───────────┘
      ▲                                        │
      └─────────────────play()─────────────────┘
"""

from __future__ import annotations

import os
import threading
import time
from typing import Callable, Optional

from . import config
from .models import Song

# ── Playback state ────────────────────────────────────────────────────────────

STOPPED = "STOPPED"
PLAYING = "PLAYING"
PAUSED = "PAUSED"

# ── Player ────────────────────────────────────────────────────────────────────

# Global player instance for the convenience module-level API
_player: Optional["AudioPlayer"] = None


def _get_player() -> "AudioPlayer":
    global _player
    if _player is None:
        _player = AudioPlayer()
    return _player


class AudioPlayer:
    """Audio player using pydub for playback.

    Uses pydub's ``play()`` function, which delegates to the system's
    ffmpeg/avplay.  Playback runs in a background thread so the UI
    remains responsive.
    """

    def __init__(self):
        self._state: str = STOPPED
        self._current_song: Song | None = None
        self._volume: float = config.DEFAULT_VOLUME
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._paused_event = threading.Event()
        self._seek_to: float | None = None
        self._elapsed_sec: float = 0.0

        # Callbacks
        self._on_state_change: list[Callable[[str], None]] = []
        self._on_track_change: list[Callable[[Song | None], None]] = []
        self._on_progress: list[Callable[[float], None]] = []

    # ── properties ───────────────────────────────────────────────────────────

    @property
    def state(self) -> str:
        return self._state

    @property
    def current_song(self) -> Song | None:
        return self._current_song

    @property
    def volume(self) -> float:
        return self._volume

    @volume.setter
    def volume(self, value: float) -> None:
        self._volume = max(0.0, min(1.0, value))

    @property
    def elapsed_sec(self) -> float:
        with self._lock:
            return self._elapsed_sec

    @property
    def is_playing(self) -> bool:
        return self._state == PLAYING

    @property
    def is_paused(self) -> bool:
        return self._state == PAUSED

    @property
    def is_stopped(self) -> bool:
        return self._state == STOPPED

    # ── callbacks ────────────────────────────────────────────────────────────

    def on_state_change(self, callback: Callable[[str], None]) -> None:
        self._on_state_change.append(callback)

    def on_track_change(self, callback: Callable[[Song | None], None]) -> None:
        self._on_track_change.append(callback)

    def on_progress(self, callback: Callable[[float], None]) -> None:
        self._on_progress.append(callback)

    # ── controls ─────────────────────────────────────────────────────────────

    def play(self, song: Song | None = None) -> None:
        """Start playback.

        If *song* is provided, begins playing that song.
        If omitted and a previous song was paused, resumes.
        If omitted and nothing was loaded, does nothing.
        """
        with self._lock:
            if song is not None:
                self._current_song = song
                self._elapsed_sec = 0.0
                self._notify_track_change()

            if self._current_song is None:
                return

            if self._state == PAUSED and song is None:
                # Resume from pause
                self._paused_event.clear()
                self._state = PLAYING
                self._notify_state_change()
                return

            self._stop_event.set()
            self._state = PLAYING
            self._notify_state_change()

        # Start playback thread
        self._stop_event.clear()
        self._paused_event.clear()
        self._thread = threading.Thread(
            target=self._playback_loop,
            daemon=True,
            name="music-player",
        )
        self._thread.start()

    def pause(self) -> None:
        """Pause playback."""
        if self._state != PLAYING:
            return
        with self._lock:
            self._state = PAUSED
            self._notify_state_change()
        self._paused_event.set()

    def resume(self) -> None:
        """Resume from pause."""
        if self._state != PAUSED:
            return
        with self._lock:
            self._state = PLAYING
            self._notify_state_change()
        self._paused_event.clear()

    def stop(self) -> None:
        """Stop playback and reset elapsed time."""
        self._stop_event.set()
        self._paused_event.set()
        with self._lock:
            self._state = STOPPED
            self._elapsed_sec = 0.0
            self._notify_state_change()

    def seek(self, seconds: float) -> None:
        """Seek to *seconds* in the current track."""
        if self._current_song is None:
            return
        clamped = max(0.0, min(self._current_song.duration_sec, seconds))
        with self._lock:
            self._seek_to = clamped

    def toggle_play_pause(self) -> None:
        """Toggle between playing and paused."""
        if self._state == PLAYING:
            self.pause()
        elif self._state == PAUSED:
            self.resume()
        else:
            self.play()

    # ── internal ─────────────────────────────────────────────────────────────

    def _playback_loop(self) -> None:
        """Background thread for actual audio playback."""
        song = self._current_song
        if song is None:
            return

        try:
            from pydub import AudioSegment
            from pydub.playback import play as pydub_play

            # Load the audio file
            segment = AudioSegment.from_file(song.filepath)
            if self._volume < 1.0:
                segment = segment - ((1.0 - self._volume) * 10)  # approximate dB

            # Play in a separate thread so we can interrupt
            play_thread = threading.Thread(
                target=pydub_play,
                args=(segment,),
                daemon=True,
                name="pydub-output",
            )
            play_thread.start()

            # Simulate elapsed-time tracking
            sample_rate = segment.frame_rate or 44100
            sample_width = segment.sample_width or 2
            channels = segment.channels or 2
            bytes_per_sec = sample_rate * sample_width * channels
            total_bytes = len(segment.raw_data)
            duration = total_bytes / max(1, bytes_per_sec)

            tick = 0.05  # 50 ms update interval
            while not self._stop_event.is_set():
                if self._paused_event.is_set():
                    time.sleep(tick)
                    continue

                # Handle seek
                seek = self._seek_to
                if seek is not None:
                    with self._lock:
                        self._elapsed_sec = seek
                        self._seek_to = None

                time.sleep(tick)
                with self._lock:
                    if self._state == PLAYING:
                        self._elapsed_sec += tick

                self._notify_progress()

                # Check for end of track
                with self._lock:
                    if self._elapsed_sec >= duration:
                        break

            # Cleanup
            self._stop_event.set()
            with self._lock:
                if self._state == PLAYING:
                    self._state = STOPPED
                    self._elapsed_sec = 0.0
                    self._notify_state_change()

        except ImportError:
            # pydub not available — fallback: simulate elapsed time only
            self._simulate_playback(song)
        except Exception:
            # Silently handle playback errors (e.g. missing codec)
            with self._lock:
                self._state = STOPPED
                self._elapsed_sec = 0.0
                self._notify_state_change()

    def _simulate_playback(self, song: Song) -> None:
        """Fallback: simulate playback progress without audio output."""
        duration = song.duration_sec if song.duration_sec > 0 else 210.0
        tick = 0.05
        while not self._stop_event.is_set():
            if self._paused_event.is_set():
                time.sleep(tick)
                continue
            time.sleep(tick)
            with self._lock:
                if self._state == PLAYING:
                    self._elapsed_sec += tick
            self._notify_progress()
            with self._lock:
                if self._elapsed_sec >= duration:
                    break
        with self._lock:
            if self._state == PLAYING:
                self._state = STOPPED
                self._elapsed_sec = 0.0
                self._notify_state_change()

    def _notify_state_change(self) -> None:
        state = self._state
        for cb in self._on_state_change:
            try:
                cb(state)
            except Exception:
                pass

    def _notify_track_change(self) -> None:
        song = self._current_song
        for cb in self._on_track_change:
            try:
                cb(song)
            except Exception:
                pass

    def _notify_progress(self) -> None:
        with self._lock:
            elapsed = self._elapsed_sec
        for cb in self._on_progress:
            try:
                cb(elapsed)
            except Exception:
                pass


# ── Module-level convenience API ──────────────────────────────────────────────

def get_player() -> AudioPlayer:
    """Return the global player instance."""
    return _get_player()


def play(song: Song | None = None) -> None:
    """Start or resume playback."""
    _get_player().play(song)


def pause() -> None:
    """Pause playback."""
    _get_player().pause()


def resume() -> None:
    """Resume from pause."""
    _get_player().resume()


def stop() -> None:
    """Stop playback."""
    _get_player().stop()


def seek(seconds: float) -> None:
    """Seek to a position in the current track."""
    _get_player().seek(seconds)


def toggle_play_pause() -> None:
    """Toggle between playing and paused."""
    _get_player().toggle_play_pause()


def get_state() -> str:
    """Return the current playback state (STOPPED, PLAYING, PAUSED)."""
    return _get_player().state


def get_current_song() -> Song | None:
    """Return the currently playing song, or None."""
    return _get_player().current_song


def get_elapsed_sec() -> float:
    """Return elapsed seconds of the current track."""
    return _get_player().elapsed_sec


def get_volume() -> float:
    """Return the current volume (0.0 – 1.0)."""
    return _get_player().volume


def set_volume(value: float) -> None:
    """Set the volume (0.0 – 1.0)."""
    _get_player().volume = value


def is_playing() -> bool:
    return _get_player().is_playing


def is_paused() -> bool:
    return _get_player().is_paused


def is_stopped() -> bool:
    return _get_player().is_stopped
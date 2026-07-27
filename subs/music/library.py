"""
Music library manager — loads, caches, and provides access to the
music collection.

The ``Library`` class wraps the raw scan/cache logic from
:mod:`~subs.music.metadata` and provides a convenient singleton-like
accessor for the rest of the application.
"""

from __future__ import annotations

import os
import threading
from typing import Callable, Optional

from . import config
from .models import Library as LibraryModel, Artist, Album, Song
from .metadata import scan_library, write_cache, read_cache, is_cache_valid


class Library:
    """Music library manager.

    Usage::

        lib = Library()
        lib.scan()                  # full scan (or load from cache if valid)
        for artist in lib.artists:
            ...
    """

    def __init__(self, music_dir: str | None = None):
        self._music_dir = os.path.abspath(music_dir or config.MUSIC_DIR)
        self._library: LibraryModel | None = None
        self._lock = threading.Lock()
        self._on_change: list[Callable[[], None]] = []

    # ── properties that delegate to the in-memory model ──────────────────────

    @property
    def artists(self) -> list[Artist]:
        if self._library is None:
            return []
        return self._library.artists

    @property
    def albums(self) -> list[Album]:
        if self._library is None:
            return []
        return self._library.albums

    @property
    def songs(self) -> list[Song]:
        if self._library is None:
            return []
        return self._library.songs

    @property
    def song_count(self) -> int:
        if self._library is None:
            return 0
        return self._library.song_count

    @property
    def album_count(self) -> int:
        if self._library is None:
            return 0
        return self._library.album_count

    @property
    def artist_count(self) -> int:
        if self._library is None:
            return 0
        return self._library.artist_count

    @property
    def is_loaded(self) -> bool:
        return self._library is not None

    # ── change listeners ─────────────────────────────────────────────────────

    def on_change(self, callback: Callable[[], None]) -> None:
        """Register a callback invoked when the library is (re)scanned."""
        self._on_change.append(callback)

    # ── scanning / loading ───────────────────────────────────────────────────

    def scan(self, force: bool = False, use_cache: bool = True) -> None:
        """Scan the music directory and populate the library.

        If *use_cache* is True (default) and a valid cache exists, loads
        from cache instead of re-scanning.  Set *force* to True to
        always re-scan and re-cache.
        """
        with self._lock:
            if not force and use_cache and is_cache_valid():
                cached = read_cache()
                if cached is not None:
                    self._library = cached
                    self._notify()
                    return

            # Full scan
            self._library = scan_library(self._music_dir)

            # Write cache
            if self._library.artists:
                try:
                    write_cache(self._library)
                except OSError:
                    pass  # non-fatal; cache is a convenience

            self._notify()

    def load(self, path: str | None = None) -> bool:
        """Load from a metadata cache file without scanning.

        Returns True if the cache was loaded successfully.
        """
        cached = read_cache(path)
        if cached is None:
            return False
        with self._lock:
            self._library = cached
            self._notify()
        return True

    def reload(self) -> None:
        """Force a full re-scan and re-cache."""
        self.scan(force=True, use_cache=False)

    # ── lookup helpers ───────────────────────────────────────────────────────

    def get_artist(self, name: str) -> Optional[Artist]:
        if self._library is None:
            return None
        return self._library.get_artist(name)

    def get_album(self, name: str, artist: str) -> Optional[Album]:
        if self._library is None:
            return None
        return self._library.get_album(name, artist)

    def get_song(self, artist: str, album: str, title: str) -> Optional[Song]:
        """Look up a specific song by artist, album, and title."""
        al = self.get_album(album, artist)
        if al is None:
            return None
        for s in al.songs:
            if s.title == title:
                return s
        return None

    # ── internal ─────────────────────────────────────────────────────────────

    def _notify(self) -> None:
        for cb in self._on_change:
            try:
                cb()
            except Exception:
                pass
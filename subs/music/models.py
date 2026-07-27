"""
Data models for the music library.

::

    Artist  ──1:N──►  Album  ──1:N──►  Song

Each model carries enough metadata to power the iPod Classic UI screens
(Music > Artists, Music > Albums, Music > Songs, Now Playing).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Song:
    """A single audio track."""

    title: str
    """Display title (extracted from filename or ID3 tag)."""

    track_number: int
    """Track number on the album (0 if unknown)."""

    filename: str
    """Basename of the audio file, e.g. ``01 - Intro.mp3``."""

    relpath: str
    """Path relative to the music library root, e.g.
    ``Artist/Album/01 - Intro.mp3``."""

    filepath: str
    """Absolute filesystem path to the audio file."""

    duration_sec: float = 0.0
    """Duration in seconds (from pydub or ffprobe)."""

    bitrate_kbps: int = 0
    """Audio bitrate in kbps (0 if unknown)."""

    sample_rate_hz: int = 0
    """Sample rate in Hz (0 if unknown)."""

    format: str = ""
    """File format extension (lowercase, no dot), e.g. ``mp3``."""

    artist_name: str = ""
    """Artist name this song belongs to (inherited from directory)."""

    album_name: str = ""
    """Album name this song belongs to (inherited from directory)."""

    @property
    def display_title(self) -> str:
        """Title suitable for the Now Playing screen."""
        return self.title

    @property
    def display_artist(self) -> str:
        """Artist name for display."""
        return self.artist_name or "Unknown Artist"

    @property
    def display_album(self) -> str:
        """Album name for display."""
        return self.album_name or "Unknown Album"

    @property
    def file_ext(self) -> str:
        """File extension without dot, e.g. ``mp3``."""
        return os.path.splitext(self.filename)[1].lstrip(".").lower()


@dataclass
class Album:
    """A collection of songs by a single artist."""

    name: str
    """Album title."""

    artist: str
    """Artist name."""

    songs: list[Song] = field(default_factory=list)
    """Songs on this album, in track order."""

    cover_art_path: Optional[str] = None
    """Absolute path to cover art image, or None."""

    year: int = 0
    """Release year (0 if unknown)."""

    @property
    def song_count(self) -> int:
        return len(self.songs)

    @property
    def duration_sec(self) -> float:
        return sum(s.duration_sec for s in self.songs)


@dataclass
class Artist:
    """A musical artist with their albums."""

    name: str
    """Artist name."""

    albums: list[Album] = field(default_factory=list)
    """Albums by this artist, sorted alphabetically."""

    cover_art_path: Optional[str] = None
    """Absolute path to an artist-level image, or None."""

    @property
    def album_count(self) -> int:
        return len(self.albums)

    @property
    def song_count(self) -> int:
        return sum(a.song_count for a in self.albums)

    @property
    def song_list(self) -> list[Song]:
        """Flattened list of all songs across all albums."""
        return [s for a in self.albums for s in a.songs]


@dataclass
class Library:
    """The complete in-memory music library."""

    artists: list[Artist] = field(default_factory=list)
    """All artists, sorted alphabetically."""

    @property
    def albums(self) -> list[Album]:
        """Flattened list of all albums across all artists."""
        return [a for artist in self.artists for a in artist.albums]

    @property
    def songs(self) -> list[Song]:
        """Flattened list of all songs across all albums."""
        return [s for a in self.albums for s in a.songs]

    @property
    def song_count(self) -> int:
        return len(self.songs)

    @property
    def album_count(self) -> int:
        return len(self.albums)

    @property
    def artist_count(self) -> int:
        return len(self.artists)

    def get_artist(self, name: str) -> Optional[Artist]:
        """Look up an artist by name (exact match)."""
        for a in self.artists:
            if a.name == name:
                return a
        return None

    def get_album(self, name: str, artist: str) -> Optional[Album]:
        """Look up an album by name and artist."""
        a = self.get_artist(artist)
        if a is None:
            return None
        for al in a.albums:
            if al.name == name:
                return al
        return None
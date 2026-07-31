"""Config-driven music library loader.

Loads song metadata from ``files/library.json`` and provides the same
``Song``, ``Album``, ``Artist`` dataclass interface as the old stub_data.py,
but driven by a user-editable configuration file.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Song:
    title: str
    track_number: int
    artist_name: str
    album_name: str
    duration_sec: float
    filepath: str = ""
    cover_art_path: Optional[str] = None
    format: str = "mp3"

    def __post_init__(self):
        # Infer format from the file extension if not explicitly set
        if self.filepath:
            ext = os.path.splitext(self.filepath)[1].lower()
            self.format = ext.lstrip(".") if ext else "mp3"


@dataclass
class Album:
    name: str
    artist: str
    songs: list = field(default_factory=list)
    cover_art_path: Optional[str] = None

    @property
    def song_count(self) -> int:
        return len(self.songs)


@dataclass
class Artist:
    name: str
    albums: list = field(default_factory=list)

    @property
    def album_count(self) -> int:
        return len(self.albums)

    @property
    def song_count(self) -> int:
        return sum(a.song_count for a in self.albums)

    @property
    def song_list(self) -> list:
        return [s for a in self.albums for s in a.songs]


class LocalLibrary:
    """Music library loaded from ``files/library.json``."""

    def __init__(self, config_path: str = "files/library.json"):
        self.config_path = config_path
        self._artists: list[Artist] = []
        self._albums: list[Album] = []
        self._songs: list[Song] = []
        self._playlists: list[dict] = []
        self._load()

    @property
    def artists(self) -> list[Artist]:
        return self._artists

    @property
    def albums(self) -> list[Album]:
        return self._albums

    @property
    def songs(self) -> list[Song]:
        return self._songs

    @property
    def playlists(self) -> list[dict]:
        return self._playlists

    @property
    def song_count(self) -> int:
        return len(self._songs)

    @property
    def album_count(self) -> int:
        return len(self._albums)

    @property
    def artist_count(self) -> int:
        return len(self._artists)

    def get_album(self, name: str, artist: str) -> Optional[Album]:
        for a in self._artists:
            if a.name == artist:
                for al in a.albums:
                    if al.name == name:
                        return al
        return None

    def get_playlist_songs(self, playlist_name: str) -> list[Song]:
        """Return the list of Song objects for a named playlist."""
        for pl in self._playlists:
            if pl["name"] == playlist_name:
                titles = [t.strip() for t in pl.get("songs", [])]
                # Match by title (case-insensitive), return in playlist order
                title_map = {s.title.lower(): s for s in self._songs}
                return [title_map[t.lower()] for t in titles if t.lower() in title_map]
        return []

    def _load(self):
        """Load and parse the JSON config file."""
        if not os.path.exists(self.config_path):
            self._artists = []
            self._albums = []
            self._songs = []
            self._playlists = []
            return

        with open(self.config_path, "r") as f:
            data = json.load(f)

        # Parse songs
        song_dicts = data.get("songs", [])
        songs = []
        for sd in song_dicts:
            song = Song(
                title=sd.get("title", "Unknown"),
                track_number=sd.get("track", 0),
                artist_name=sd.get("artist", "Unknown Artist"),
                album_name=sd.get("album", "Unknown Album"),
                duration_sec=float(sd.get("duration_sec", 0)),
                filepath=sd.get("file", ""),
                cover_art_path=sd.get("backup_cover"),
            )
            songs.append(song)
        self._songs = songs

        # Parse playlists
        self._playlists = data.get("playlists", [])

        # Build artist → album → song tree
        artist_map = {}
        for song in songs:
            artist_name = song.artist_name
            album_name = song.album_name

            if artist_name not in artist_map:
                artist_map[artist_name] = {"artist": Artist(name=artist_name), "albums": {}}

            artist_entry = artist_map[artist_name]
            if album_name not in artist_entry["albums"]:
                # Find cover art for this album from first song that has it
                cover = song.cover_art_path if song.cover_art_path else None
                artist_entry["albums"][album_name] = Album(
                    name=album_name,
                    artist=artist_name,
                    songs=[],
                    cover_art_path=cover,
                )
            artist_entry["albums"][album_name].songs.append(song)

        # Build final lists
        self._artists = []
        self._albums = []
        for artist_name in sorted(artist_map.keys(), key=str.lower):
            entry = artist_map[artist_name]
            artist = entry["artist"]
            album_list = list(entry["albums"].values())
            album_list.sort(key=lambda a: a.name.lower())
            artist.albums = album_list
            self._artists.append(artist)
            self._albums.extend(album_list)
"""
Metadata scanning and caching for the music library.

The scanner walks the ``files/music/`` directory tree, parses the
directory structure to infer artist / album / song metadata, optionally
uses pydub to read audio details (duration, bitrate, sample rate), and
caches the result in a JSON file for fast subsequent loads.

Directory convention::

    files/music/
    ├── Artist Name/
    │   ├── cover.jpg                <-- artist-level cover art (optional)
    │   ├── Album Name/
    │   │   ├── cover.jpg            <-- album-level cover art
    │   │   ├── 01 - Song Title.mp3
    │   │   ├── 02 - Song Title.mp3
    │   │   └── ...
    │   └── ...
    └── ...
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Optional

from . import config
from .models import Song, Album, Artist, Library

# ── helpers ───────────────────────────────────────────────────────────────────

_TRACK_PATTERN = re.compile(
    r"^(?P<num>\d{1,3})\s*[-.]?\s*(?P<title>.+?)(?:\.\w+)?$"
)


def _parse_track_number(filename: str) -> tuple[int, str]:
    """Extract the track number and title from a filename.

    Handles patterns like::

        01 - Song Title.mp3      →  (1, "Song Title")
        01-Song Title.mp3        →  (1, "Song Title")
        01. Song Title.mp3       →  (1, "Song Title")
        01 Song Title.mp3        →  (1, "Song Title")
        Song Title.mp3           →  (0, "Song Title")
    """
    name, _ = os.path.splitext(filename)
    m = _TRACK_PATTERN.match(name)
    if m:
        return int(m.group("num")), m.group("title").strip()
    return 0, name.strip()


def _find_cover_art(directory: str) -> Optional[str]:
    """Look for a cover art image in *directory*.

    Returns the absolute path to the first match, or None.
    """
    for fname in config.COVER_ART_NAMES:
        path = os.path.join(directory, fname)
        if os.path.isfile(path):
            return os.path.abspath(path)
    # Also check a .cover_art subdirectory
    cover_dir = os.path.join(directory, ".cover_art")
    if os.path.isdir(cover_dir):
        for fname in os.listdir(cover_dir):
            ext = os.path.splitext(fname)[1].lower()
            if ext in (".jpg", ".jpeg", ".png", ".bmp", ".gif"):
                return os.path.abspath(os.path.join(cover_dir, fname))
    return None


def _probe_audio(filepath: str) -> dict:
    """Use pydub to read audio metadata from *filepath*.

    Returns a dict with keys ``duration_sec``, ``bitrate_kbps``,
    ``sample_rate_hz``.  Returns zero-filled dict on failure.
    """
    result = {"duration_sec": 0.0, "bitrate_kbps": 0, "sample_rate_hz": 0}
    try:
        from pydub.utils import mediainfo
        info = mediainfo(filepath)
        if info:
            dur_str = info.get("duration", "0")
            try:
                result["duration_sec"] = float(dur_str)
            except (ValueError, TypeError):
                pass
            br_str = info.get("bit_rate", "0")
            try:
                result["bitrate_kbps"] = int(br_str) // 1000
            except (ValueError, TypeError):
                pass
            sr_str = info.get("sample_rate", "0")
            try:
                result["sample_rate_hz"] = int(sr_str)
            except (ValueError, TypeError):
                pass
    except Exception:
        pass
    return result


# ── scanner ───────────────────────────────────────────────────────────────────

def _is_audio_file(filename: str) -> bool:
    ext = os.path.splitext(filename)[1].lower()
    return ext in config.SUPPORTED_EXTENSIONS


def scan_library(music_dir: str | None = None) -> Library:
    """Walk *music_dir* and build a ``Library`` from the directory tree.

    If *music_dir* is None, uses ``config.MUSIC_DIR``.
    """
    root = os.path.abspath(music_dir or config.MUSIC_DIR)
    lib = Library()

    if not os.path.isdir(root):
        return lib  # empty library

    # Iterate over artist directories
    artist_names = sorted(
        d for d in os.listdir(root)
        if os.path.isdir(os.path.join(root, d)) and not d.startswith(".")
    )

    for artist_name in artist_names:
        artist_dir = os.path.join(root, artist_name)
        artist_cover = _find_cover_art(artist_dir)
        artist = Artist(name=artist_name, cover_art_path=artist_cover)

        # Iterate over album directories inside the artist directory
        album_names = sorted(
            d for d in os.listdir(artist_dir)
            if os.path.isdir(os.path.join(artist_dir, d)) and not d.startswith(".")
        )

        for album_name in album_names:
            album_dir = os.path.join(artist_dir, album_name)
            album_cover = _find_cover_art(album_dir)
            album = Album(
                name=album_name,
                artist=artist_name,
                cover_art_path=album_cover,
            )

            # Iterate over audio files in the album directory
            audio_files = sorted(
                f for f in os.listdir(album_dir)
                if _is_audio_file(f)
            )

            for filename in audio_files:
                filepath = os.path.join(album_dir, filename)
                relpath = os.path.relpath(filepath, root)
                track_num, title = _parse_track_number(filename)
                ext = os.path.splitext(filename)[1].lstrip(".").lower()

                # Probe with pydub
                probe = _probe_audio(filepath)

                song = Song(
                    title=title,
                    track_number=track_num,
                    filename=filename,
                    relpath=relpath,
                    filepath=filepath,
                    duration_sec=probe["duration_sec"],
                    bitrate_kbps=probe["bitrate_kbps"],
                    sample_rate_hz=probe["sample_rate_hz"],
                    format=ext,
                    artist_name=artist_name,
                    album_name=album_name,
                )
                album.songs.append(song)

            # Sort songs by track number
            album.songs.sort(key=lambda s: s.track_number)
            artist.albums.append(album)

        lib.artists.append(artist)

    return lib


# ── cache ─────────────────────────────────────────────────────────────────────

def _song_to_dict(song: Song) -> dict:
    return {
        "title": song.title,
        "track_number": song.track_number,
        "filename": song.filename,
        "relpath": song.relpath,
        "duration_sec": song.duration_sec,
        "bitrate_kbps": song.bitrate_kbps,
        "sample_rate_hz": song.sample_rate_hz,
        "format": song.format,
        "artist_name": song.artist_name,
        "album_name": song.album_name,
    }


def _album_to_dict(album: Album) -> dict:
    return {
        "name": album.name,
        "artist": album.artist,
        "cover_art_path": album.cover_art_path,
        "year": album.year,
        "songs": [_song_to_dict(s) for s in album.songs],
    }


def _artist_to_dict(artist: Artist) -> dict:
    return {
        "name": artist.name,
        "cover_art_path": artist.cover_art_path,
        "albums": [_album_to_dict(a) for a in artist.albums],
    }


def _dict_to_song(d: dict) -> Song:
    return Song(
        title=d["title"],
        track_number=d["track_number"],
        filename=d["filename"],
        relpath=d["relpath"],
        filepath=os.path.join(config.MUSIC_DIR, d["relpath"]),
        duration_sec=d.get("duration_sec", 0.0),
        bitrate_kbps=d.get("bitrate_kbps", 0),
        sample_rate_hz=d.get("sample_rate_hz", 0),
        format=d.get("format", ""),
        artist_name=d.get("artist_name", ""),
        album_name=d.get("album_name", ""),
    )


def _dict_to_album(d: dict) -> Album:
    return Album(
        name=d["name"],
        artist=d["artist"],
        cover_art_path=d.get("cover_art_path"),
        year=d.get("year", 0),
        songs=[_dict_to_song(s) for s in d.get("songs", [])],
    )


def _dict_to_artist(d: dict) -> Artist:
    return Artist(
        name=d["name"],
        cover_art_path=d.get("cover_art_path"),
        albums=[_dict_to_album(a) for a in d.get("albums", [])],
    )


def write_cache(library: Library, path: str | None = None) -> None:
    """Serialize the library to a JSON metadata cache file."""
    dest = path or config.METADATA_FILE
    data = {
        "_version": 1,
        "_generated_at": time.time(),
        "artists": [_artist_to_dict(a) for a in library.artists],
    }
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def read_cache(path: str | None = None) -> Library | None:
    """Load the library from a JSON metadata cache file.

    Returns ``None`` if the cache file doesn't exist or is corrupt.
    """
    src = path or config.METADATA_FILE
    if not os.path.isfile(src):
        return None
    try:
        with open(src) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict) or "artists" not in data:
        return None
    lib = Library()
    for d in data["artists"]:
        lib.artists.append(_dict_to_artist(d))
    return lib


def is_cache_valid(path: str | None = None) -> bool:
    """Check if the metadata cache is newer than any music file."""
    cache_path = path or config.METADATA_FILE
    if not os.path.isfile(cache_path):
        return False
    cache_mtime = os.path.getmtime(cache_path)
    music_dir = config.MUSIC_DIR
    if not os.path.isdir(music_dir):
        return False
    for dirpath, _dirnames, filenames in os.walk(music_dir):
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            if os.path.isfile(fpath) and os.path.getmtime(fpath) > cache_mtime:
                return False
    return True
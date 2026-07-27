"""
Configuration for the music subsystem.

All paths are relative to the project root (``/home/al999/nuPod``)
or can be overridden via environment variables.
"""

import os

# ── Project root ──────────────────────────────────────────────────────────────

# Detect the project root: walk up from this file's location until we find main.py
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))

# Allow override via env var for testing or alternate setups
PROJECT_ROOT = os.environ.get("NUPOD_ROOT", _PROJECT_ROOT)


# ── Music library paths ───────────────────────────────────────────────────────

# Top-level directory where music files live
MUSIC_DIR = os.environ.get(
    "NUPOD_MUSIC_DIR",
    os.path.join(PROJECT_ROOT, "files", "music"),
)

# Metadata cache file (JSON)
METADATA_FILE = os.environ.get(
    "NUPOD_METADATA_FILE",
    os.path.join(MUSIC_DIR, ".metadata_cache.json"),
)

# Directory where the sample music is placed (so we can seed it)
SAMPLE_MUSIC_DIR = os.environ.get(
    "NUPOD_SAMPLE_MUSIC_DIR",
    os.path.join(MUSIC_DIR, "sample"),
)


# ── Supported audio formats ───────────────────────────────────────────────────

SUPPORTED_EXTENSIONS = {
    ".mp3",
    ".flac",
    ".ogg",
    ".m4a",
    ".wav",
    ".aiff",
    ".wma",
}

# Cover art filenames to look for (case-insensitive match)
COVER_ART_NAMES = {
    "cover.jpg",
    "cover.png",
    "folder.jpg",
    "folder.png",
    "artwork.jpg",
    "artwork.png",
    "album.jpg",
    "album.png",
    "front.jpg",
    "front.png",
}


# ── Player defaults ───────────────────────────────────────────────────────────

DEFAULT_VOLUME = 0.6       # 0.0 – 1.0
CROSSFADE_MS = 0           # crossfade between tracks in ms
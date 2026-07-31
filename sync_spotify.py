#!/usr/bin/env python3
"""
Spotify sync script — downloads music from Spotify via zotify and populates
``files/library.json`` with the correct file paths, durations, and metadata.

Usage
-----
    1. Add Spotify album/playlist/track URLs to the ``"download_from_spotify"``
       section of ``files/library.json``:

           {
             "download_from_spotify": {
               "albums": [
                 "https://open.spotify.com/album/5eAxOaagD8GHJf1fh5UQy8"
               ],
               "playlists": [
                 "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
               ],
               "tracks": [
                 "https://open.spotify.com/track/6rqhFgbbKwnb9MLmUQDhG6"
               ]
             },
             "songs": [...],
             "playlists": [...]
           }

    2. Optionally, set ``backup_cover`` to a path for an image to show when
       no cover art is found:

           "backup_cover": "files/backup_cover.jpg"

    3. Run this script:

           python sync_spotify.py

    4. The script will:
       - Download all missing tracks from Spotify via zotify
       - Scan the downloaded files and extract metadata (duration)
       - Update ``files/library.json`` with file paths, durations,
         track numbers, and a ``backup_cover`` field pointing to the backup image

Requirements
------------
    pip install git+https://github.com/Googolplexed0/zotify.git
    ffmpeg (for pydub / duration detection)
"""

import json
import os
import re
import subprocess
import sys

# ── Config ───────────────────────────────────────────────────────────────────

LIBRARY_PATH = "files/library.json"
ZOTIFY_ROOT = os.path.abspath("files/music")
SONG_ARCHIVE = os.path.join(os.getcwd(), ".song_archive")
BACKUP_COVER = "files/music/MISSING_COVER.png"  # generic "no cover" placeholder


# ── Helpers ──────────────────────────────────────────────────────────────────

def _load_library() -> dict:
    """Load the library config, returning an empty structure if missing."""
    if not os.path.exists(LIBRARY_PATH):
        print(f"[!] {LIBRARY_PATH} not found — creating skeleton.")
        return {"songs": [], "playlists": [], "download_from_spotify": {"albums": [], "playlists": [], "tracks": []}}
    with open(LIBRARY_PATH, "r") as f:
        return json.load(f)


def _save_library(data: dict) -> None:
    """Write the library config back to disk."""
    with open(LIBRARY_PATH, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print(f"[✓] Updated {LIBRARY_PATH}")


def _get_duration_sec(filepath: str) -> float:
    """Get audio duration in seconds via ffprobe (fast, no decode)."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                filepath,
            ],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return round(float(result.stdout.strip()), 1)
    except Exception:
        pass
    return 0.0


def _check_zotify() -> bool:
    """Check that zotify is available."""
    for attempt in (["python", "-m", "zotify", "--version"], ["zotify", "--version"]):
        try:
            subprocess.run(attempt, capture_output=True, timeout=15)
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return False


def _guess_zotify_command() -> list[str]:
    """Return the command prefix for running zotify."""
    try:
        subprocess.run(
            ["python", "-m", "zotify", "--version"],
            capture_output=True, timeout=15,
        )
        return ["python", "-m", "zotify"]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return ["zotify"]


def _normalise(s: str) -> str:
    """Normalise a string for filename matching."""
    s = s.lower().strip()
    s = re.sub(r"[_\-.,'!?()/\\]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _match_song_filename(song: dict, filepath: str) -> bool:
    """Check if *filepath* matches *song*'s title + artist."""
    filename = os.path.splitext(os.path.basename(filepath))[0]
    fn_norm = _normalise(filename)
    title_norm = _normalise(song.get("title", ""))
    artist_norm = _normalise(song.get("artist", ""))
    return title_norm in fn_norm and artist_norm in fn_norm


# ── Download phase ───────────────────────────────────────────────────────────

def _collect_urls(data: dict) -> list[str]:
    """Collect all download URLs from the config."""
    cfg = data.get("download_from_spotify", {})
    urls = []
    urls.extend(cfg.get("albums", []))
    urls.extend(cfg.get("playlists", []))
    urls.extend(cfg.get("tracks", []))
    return urls


def download_music(data: dict) -> None:
    """Run zotify for each URL in the config."""
    urls = _collect_urls(data)
    if not urls:
        print("[.] No Spotify URLs configured — skipping download.")
        return

    cmd = _guess_zotify_command()
    print(f"[zotify] Using: {' '.join(cmd)}")

    os.makedirs(ZOTIFY_ROOT, exist_ok=True)

    for url in urls:
        kind = "track" if "/track/" in url else "album" if "/album/" in url else "playlist" if "/playlist/" in url else "url"
        print(f"\n[zotify] Downloading {kind}: {url}")
        base_cmd = [*cmd, "-rp", ZOTIFY_ROOT,
                     "--song-archive-location", SONG_ARCHIVE,
                     "-ip", "True",
                     url]
        try:
            subprocess.run(base_cmd, timeout=600)
            print(f"[✓] Finished: {url}")

            # If this was a playlist, add it to library.json's playlist index
            if kind == "playlist":
                _add_playlist_to_index(data, url)
        except subprocess.TimeoutExpired:
            print(f"[!] Timed out: {url}")
        except subprocess.CalledProcessError as e:
            print(f"[!] zotify error for {url}: {e}")
        except FileNotFoundError:
            print("[!] zotify not found. Install with:")
            print("    pip install git+https://github.com/Googolplexed0/zotify.git")
            sys.exit(1)


def _add_playlist_to_index(data: dict, url: str) -> None:
    """Try to add a playlist URL to the library's playlists list if not
    already present.  The actual song names will be matched during the
    scan phase."""
    import re
    # Extract a readable name from the URL or use a placeholder
    match = re.search(r"playlist/([a-zA-Z0-9_-]+)", url)
    if not match:
        return
    pid = match.group(1)
    name = f"Spotify Playlist ({pid[:8]}...)"
    existing = [p for p in data.get("playlists", []) if p.get("name") == name]
    if not existing:
        data.setdefault("playlists", []).append({"name": name, "songs": []})
        print(f"  📋 Added playlist to library index: {name}")


# ── Scan & update phase ──────────────────────────────────────────────────────

def scan_and_update(data: dict) -> int:
    """Scan the download directory and update each song entry with
    filepath, duration_sec, and track number.

    Every song gets its ``cover`` field set to the backup cover path
    (the UI reads the real cover from the audio file's embedded tags).

    Returns the number of songs that were updated.
    """
    if not os.path.isdir(ZOTIFY_ROOT):
        print(f"[!] Download root not found: {ZOTIFY_ROOT}")
        return 0

    backup = data.get("backup_cover", BACKUP_COVER)

    audio_exts = {".mp3", ".m4a", ".ogg", ".opus", ".flac", ".aac", ".wav", ".wma"}
    downloaded = []
    for root, dirs, files in os.walk(ZOTIFY_ROOT):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if os.path.splitext(f)[1].lower() in audio_exts:
                downloaded.append(os.path.join(root, f))

    if not downloaded:
        print(f"[.] No audio files found under {ZOTIFY_ROOT}")
        return 0

    print(f"\n[scan] Found {len(downloaded)} audio files — matching to library...")

    updated = 0
    songs = data.get("songs", [])
    for song in songs:
        existing = song.get("file", "")
        if existing and os.path.exists(existing) and song.get("duration_sec", 0) > 0:
            continue

        match = None
        for fp in downloaded:
            if _match_song_filename(song, fp):
                match = fp
                break

        if match is None:
            title_norm = _normalise(song.get("title", ""))
            for fp in downloaded:
                fn_norm = _normalise(os.path.splitext(os.path.basename(fp))[0])
                if title_norm and title_norm in fn_norm:
                    match = fp
                    break

        if match is None:
            print(f"  ?  No file for: {song.get('title', '?')} — {song.get('artist', '?')}")
            continue

        rel_path = os.path.relpath(match, start=os.getcwd())
        duration = _get_duration_sec(match)

        basename = os.path.splitext(os.path.basename(match))[0]
        track_num = song.get("track", 0)
        tn_match = re.match(r"^(\d+)[\s_\-\.]", basename)
        if tn_match and (track_num == 0 or track_num is None):
            track_num = int(tn_match.group(1))

        song["file"] = rel_path
        if duration > 0:
            song["duration_sec"] = duration
        if track_num:
            song["track"] = track_num

        # Point to the backup cover — the UI reads the real art from
        # the audio file's embedded tags when this path doesn't exist.
        song["backup_cover"] = backup

        print(f"  ✓  {song.get('title', '?')} → {rel_path}")
        updated += 1

    return updated


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not _check_zotify():
        print("[!] zotify is not installed.")
        print("    Install it with:")
        print("    pip install git+https://github.com/Googolplexed0/zotify.git")
        sys.exit(1)

    print("═" * 50)
    print("  Spotify Sync — Download & Update Library")
    print("═" * 50)

    data = _load_library()
    print(f"[ ] Library has {len(data.get('songs', []))} song(s) defined")

    download_music(data)

    updated = scan_and_update(data)
    if updated > 0:
        _save_library(data)
        print(f"\n[✓] Updated {updated} song(s) in the library.")
    else:
        print("\n[.] No songs needed updating.")

    songs = data.get("songs", [])
    with_file = sum(1 for s in songs if s.get("file") and os.path.exists(s.get("file", "")))
    print(f"\nSummary: {with_file}/{len(songs)} songs have local files.")


if __name__ == "__main__":
    main()
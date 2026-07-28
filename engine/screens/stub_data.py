"""Minimal stub data for the music browser screens.

Replaces the real music library (subs/music/) with hardcoded sample data
so the UI works without needing pydub, ffprobe, or a real music collection.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Song:
    title: str
    track_number: int
    artist_name: str
    album_name: str
    duration_sec: float
    filename: str = ""
    filepath: str = ""
    relpath: str = ""
    bitrate_kbps: int = 0
    sample_rate_hz: int = 0
    format: str = "mp3"
    has_id3: bool = True


@dataclass
class Album:
    name: str
    artist: str
    songs: list = field(default_factory=list)
    cover_art_path: Optional[str] = None
    year: int = 0

    @property
    def song_count(self) -> int:
        return len(self.songs)


@dataclass
class Artist:
    name: str
    albums: list = field(default_factory=list)
    cover_art_path: Optional[str] = None

    @property
    def album_count(self) -> int:
        return len(self.albums)

    @property
    def song_count(self) -> int:
        return sum(a.song_count for a in self.albums)

    @property
    def song_list(self) -> list:
        return [s for a in self.albums for s in a.songs]


class StubLibrary:
    """In-memory stub library with hardcoded sample data."""

    def __init__(self):
        self.artists: list[Artist] = []
        self._build()

    @property
    def albums(self) -> list[Album]:
        return [a for artist in self.artists for a in artist.albums]

    @property
    def songs(self) -> list[Song]:
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

    def get_album(self, name: str, artist: str) -> Optional[Album]:
        for a in self.artists:
            if a.name == artist:
                for al in a.albums:
                    if al.name == name:
                        return al
        return None

    def _build(self):
        music_dir = "files/music"

        # ── Tame Impala / Currents ─────────────────────────────────────
        currents_songs = [
            Song("Let It Happen", 1, "Tame Impala", "Currents", 291),
            Song("Nangs", 2, "Tame Impala", "Currents", 107),
            Song("The Moment", 3, "Tame Impala", "Currents", 255),
            Song("Yes I'm Changing", 4, "Tame Impala", "Currents", 210),
            Song("Eventually", 5, "Tame Impala", "Currents", 319),
            Song("Gossip", 6, "Tame Impala", "Currents", 55),
            Song("The Less I Know The Better", 7, "Tame Impala", "Currents", 338),
            Song("Past Life", 8, "Tame Impala", "Currents", 227),
            Song("Disciples", 9, "Tame Impala", "Currents", 108),
            Song("Reality In Motion", 10, "Tame Impala", "Currents", 252),
        ]
        currents_cover = f"{music_dir}/Tame Impala/Currents/cover.jpg"
        currents = Album("Currents", "Tame Impala", currents_songs, currents_cover)
        tame_impala = Artist("Tame Impala", [currents])

        # ── Crystal Falls / Winter Garden ──────────────────────────────
        winter_songs = [
            Song("Winter Garden", 1, "Crystal Falls", "Winter Garden", 245),
            Song("Frozen Lake", 2, "Crystal Falls", "Winter Garden", 198),
            Song("First Snow", 3, "Crystal Falls", "Winter Garden", 312),
        ]
        winter_cover = f"{music_dir}/Crystal Falls/Winter Garden/cover.jpg"
        winter = Album("Winter Garden", "Crystal Falls", winter_songs, winter_cover)
        crystal_falls = Artist("Crystal Falls", [winter])

        # ── Neon Pulse / City Lights ───────────────────────────────────
        city_songs = [
            Song("City Lights", 1, "Neon Pulse", "City Lights", 267),
            Song("Neon Dream", 2, "Neon Pulse", "City Lights", 223),
            Song("Midnight Run", 3, "Neon Pulse", "City Lights", 189),
        ]
        city_cover = f"{music_dir}/Neon Pulse/City Lights/cover.jpg"
        city = Album("City Lights", "Neon Pulse", city_songs, city_cover)
        neon_pulse = Artist("Neon Pulse", [city])

        # ── Luna Wave / Ocean Blues ────────────────────────────────────
        ocean_songs = [
            Song("Ocean Blues", 1, "Luna Wave", "Ocean Blues", 278),
            Song("Tidal", 2, "Luna Wave", "Ocean Blues", 201),
            Song("Moonlit", 3, "Luna Wave", "Ocean Blues", 334),
        ]
        ocean_cover = f"{music_dir}/Luna Wave/Ocean Blues/cover.jpg"
        ocean = Album("Ocean Blues", "Luna Wave", ocean_songs, ocean_cover)
        luna_wave = Artist("Luna Wave", [ocean])

        self.artists = [tame_impala, crystal_falls, neon_pulse, luna_wave]
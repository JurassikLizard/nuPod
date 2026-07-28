"""Song list browser — all songs from the stub library, sorted alphabetically.
Selecting a song starts playback.
"""

from . import Button
from .list_screen import ListScreen
from .stub_data import StubLibrary
from hardware import audio


_library = None


def _get_library():
    global _library
    if _library is None:
        _library = StubLibrary()
    return _library


class SongsScreen(ListScreen):
    """Music > Songs: flat list of all songs."""

    def __init__(self):
        super().__init__()
        self._songs = sorted(_get_library().songs, key=lambda s: s.title.lower())

    def _get_items(self):
        return self._songs

    def _item_count(self):
        return len(self._songs)

    def _render_item(self, renderer, assets, theme, x, y, w, h, song, selected):
        text_color = theme.get("colors", {}).get("foreground", "000000")
        sel_color = theme.get("colors", {}).get("selector_text", "FFFFFF")
        color = self._hex_rgb(sel_color if selected else text_color)

        prefix = f"{song.track_number}. " if song.track_number else ""
        display = f"{prefix}{song.title}"
        self._blit_text(renderer, assets, display, x + 4, y + (h - 10) // 2, color)

    def _on_select(self, index):
        if index >= len(self._songs):
            return True
        song = self._songs[index]
        lib = _get_library()
        album = lib.get_album(song.album_name, song.artist_name)
        cover = album.cover_art_path if album else None

        audio.set_title(song.title)
        audio.set_artist(song.artist_name or "Unknown Artist")
        audio.set_album(song.album_name or "Unknown Album")
        audio.set_album_art_path(cover)
        duration = song.duration_sec if song.duration_sec > 0 else 210.0
        audio.set_track_length_sec(duration)
        audio.set_elapsed_sec(0.0)
        audio.set_play_state("PLAYING")
        return True

    def _on_back(self):
        return "back"
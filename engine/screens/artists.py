"""Music/Artists screen — browse music alphabetically by artist.
Selecting an artist shows their albums, then selecting an album shows songs.
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


class ArtistsScreen(ListScreen):
    """Music > Artists: 3-level drill-down (artist -> albums -> songs)."""

    def __init__(self):
        super().__init__()
        self._artists = _get_library().artists

    def _get_items(self):
        level = len(self._stack)
        if level == 0:
            return self._artists
        elif level == 1:
            return self._stack[-1]["items"]
        else:
            return self._stack[-1]["items"]

    def _item_count(self):
        return len(self._get_items())

    def _breadcrumb_label(self):
        if self._stack:
            return self._stack[-1]["label"]
        return ""

    def _render_item(self, renderer, assets, theme, x, y, w, h, item, selected):
        text_color = theme.get("colors", {}).get("foreground", "000000")
        sel_color = theme.get("colors", {}).get("selector_text", "FFFFFF")
        color = self._hex_rgb(sel_color if selected else text_color)

        level = len(self._stack)
        if level == 0:
            display = item.name
        elif level == 1:
            display = f"{item.name} ({item.song_count})"
        else:
            song = item
            prefix = f"{song.track_number}. " if song.track_number else ""
            display = f"{prefix}{song.title}"

        self._blit_text(renderer, assets, display, x + 4, y + (h - 10) // 2, color)

    def _on_select(self, index):
        items = self._get_items()
        if index >= len(items):
            return True

        level = len(self._stack)
        if level == 0:
            artist = items[index]
            self._push_stack(artist.name, artist.albums)
        elif level == 1:
            album = items[index]
            self._push_stack(album.name, album.songs)
        else:
            song = items[index]
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
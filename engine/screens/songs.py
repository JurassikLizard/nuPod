"""Song list browser — all songs from the local library, sorted alphabetically.
Selecting a song starts playback and queues all songs for continuous play.
"""

from . import Button
from .list_screen import ListScreen
from .local_library import LocalLibrary
from hardware import audio


_library = None


def _get_library():
    global _library
    if _library is None:
        _library = LocalLibrary()
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
        lib = _get_library()
        # Build a queue of all songs (starting from the selected one)
        queue = [
            {
                "title": s.title,
                "artist": s.artist_name,
                "album": s.album_name,
                "duration_sec": s.duration_sec,
                "filepath": s.filepath,
                "cover_art_path": s.cover_art_path,
            }
            for s in self._songs
        ]
        audio.set_queue(queue)
        audio.set_queue_pos(index)
        audio.play_current()
        return True

    def _on_back(self):
        return "back"
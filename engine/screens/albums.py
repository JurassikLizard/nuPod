"""Music/Albums screen — browse music by album.
Selecting an album shows its songs, selecting a song starts playback
queued through all songs in that album.
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


class AlbumsScreen(ListScreen):
    """Music > Albums: album list with drill-down to songs."""

    def __init__(self):
        super().__init__()
        self._albums = _get_library().albums

    def _get_items(self):
        if not self._stack:
            return self._albums
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

        if not self._stack:
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

        if not self._stack:
            album = items[index]
            self._push_stack(album.name, album.songs)
        else:
            song = items[index]
            # Queue all songs in this album, starting from the selected one
            album = self._albums[self._stack[0]["items"].index(self._albums)]
            songs = album.songs
            queue = [
                {
                    "title": s.title,
                    "artist": s.artist_name,
                    "album": s.album_name,
                    "duration_sec": s.duration_sec,
                    "filepath": s.filepath,
                    "cover_art_path": s.cover_art_path,
                }
                for s in songs
            ]
            audio.set_queue(queue)
            start_idx = next(i for i, s in enumerate(songs) if s.title == song.title)
            audio.set_queue_pos(start_idx)
            audio.play_current()
        return True

    def _on_back(self):
        return "back"
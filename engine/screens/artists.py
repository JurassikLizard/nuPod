"""Music/Artists screen — browse music alphabetically by artist.
Selecting an artist shows their albums, then selecting an album shows songs.
Selecting a song starts playback queued through all songs by that artist.
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
            # Queue all songs by this artist, starting from the selected one
            artist = next(a for a in self._artists if a.albums is self._stack[0]["items"])
            songs = artist.song_list
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
            # Find the index of the selected song in the artist's song list
            start_idx = next(i for i, s in enumerate(songs) if s.title == song.title and s.album_name == song.album_name)
            audio.set_queue_pos(start_idx)
            audio.play_current()
        return True

    def _on_back(self):
        return "back"
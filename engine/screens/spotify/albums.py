"""Spotify > Albums — browse the user's saved albums.

Level 0: List of saved albums
Level 1: List of tracks in the selected album
Selecting a track starts playback on the Spotify Connect device.
"""

from ..list_screen import ListScreen
from .. import Button
from engine.spotify_client import get_client
from . import play_spotify_track


class SpotifyAlbumsScreen(ListScreen):
    """Spotify > Albums: drill-down to tracks."""

    def __init__(self):
        super().__init__()
        self._albums = []
        self._tracks_cache = {}  # album_id -> list of track dicts
        self._load_albums()

    def _load_albums(self):
        client = get_client()
        if client.is_authenticated():
            self._albums = client.get_saved_albums(limit=50)
        else:
            self._albums = []

    def _get_items(self):
        if not self._stack:
            return self._albums
        return self._stack[-1]["items"]

    def _item_count(self):
        return len(self._get_items())

    def _render_item(self, renderer, assets, theme, x, y, w, h, item, selected):
        text_color = theme.get("colors", {}).get("foreground", "000000")
        sel_color = theme.get("colors", {}).get("selector_text", "FFFFFF")
        color = self._hex_rgb(sel_color if selected else text_color)

        if not self._stack:
            display = f"{item['name']} ({item['track_count']})"
        else:
            track = item
            prefix = f"{track['track_number']}. " if track.get("track_number") else ""
            display = f"{prefix}{track['title']}"

        self._blit_text(renderer, assets, display, x + 4, y + (h - 10) // 2, color)

    def _on_select(self, index):
        items = self._get_items()
        if index >= len(items):
            return True

        if not self._stack:
            # Level 0: show album tracks
            album = items[index]
            aid = album["id"]
            if aid not in self._tracks_cache:
                client = get_client()
                tracks = client.get_album_tracks(aid, limit=50)
                self._tracks_cache[aid] = tracks
            tracks = self._tracks_cache.get(aid, [])
            if tracks:
                self._push_stack(album["name"], tracks)
        else:
            # Level 1: start playback
            self._play_track(index)
        return True

    def _play_track(self, index):
        items = self._get_items()
        if index >= len(items):
            return

        tracks = items
        uris = [t["uri"] for t in tracks if t.get("uri")]
        play_spotify_track(uris, start_index=index)

    def _on_back(self):
        return "back"
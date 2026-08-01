"""Spotify > Playlists — browse the user's Spotify playlists.

Level 0: List of playlists (name + track count)
Level 1: List of tracks in the selected playlist
Selecting a track starts playback on the Spotify Connect device.
"""

from ..list_screen import ListScreen
from .. import Button
from engine.spotify_client import get_client
from . import play_spotify_track


class SpotifyPlaylistsScreen(ListScreen):
    """Spotify > Playlists: drill-down to tracks."""

    def __init__(self):
        super().__init__()
        self._playlists = []
        self._tracks_cache = {}  # playlist_id -> list of track dicts
        self._load_playlists()

    def _load_playlists(self):
        client = get_client()
        if client.is_authenticated():
            self._playlists = client.get_playlists(limit=50)
        else:
            self._playlists = []

    def _get_items(self):
        if not self._stack:
            return self._playlists
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
            # Level 0: show playlist tracks
            playlist = items[index]
            pid = playlist["id"]
            if pid not in self._tracks_cache:
                client = get_client()
                tracks = client.get_playlist_tracks(pid, limit=100)
                self._tracks_cache[pid] = tracks
            tracks = self._tracks_cache.get(pid, [])
            if tracks:
                self._push_stack(playlist["name"], tracks)
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
"""Spotify > Artists — browse the user's followed artists.

Level 0: List of followed artists
Level 1: List of albums by the selected artist
Level 2: List of tracks in the selected album
Selecting a track starts playback on the Spotify Connect device.
"""

from ..list_screen import ListScreen
from .. import Button
from engine.spotify_client import get_client
from . import play_spotify_track


class SpotifyArtistsScreen(ListScreen):
    """Spotify > Artists: 3-level drill-down (artist -> albums -> tracks)."""

    def __init__(self):
        super().__init__()
        self._artists = []
        self._albums_cache = {}  # artist_id -> list of album dicts
        self._tracks_cache = {}  # album_id -> list of track dicts
        self._load_artists()

    def _load_artists(self):
        client = get_client()
        if client.is_authenticated():
            self._artists = client.get_followed_artists(limit=50)
        else:
            self._artists = []

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

    def _render_item(self, renderer, assets, theme, x, y, w, h, item, selected):
        text_color = theme.get("colors", {}).get("foreground", "000000")
        sel_color = theme.get("colors", {}).get("selector_text", "FFFFFF")
        color = self._hex_rgb(sel_color if selected else text_color)

        level = len(self._stack)
        if level == 0:
            display = item["name"]
        elif level == 1:
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

        level = len(self._stack)

        if level == 0:
            # Level 0: show artist's albums
            artist = items[index]
            aid = artist["id"]
            if aid not in self._albums_cache:
                client = get_client()
                albums = client.get_artist_albums(aid, limit=50)
                self._albums_cache[aid] = albums
            albums = self._albums_cache.get(aid, [])
            if albums:
                self._push_stack(artist["name"], albums)
        elif level == 1:
            # Level 1: show album tracks
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
            # Level 2: start playback
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
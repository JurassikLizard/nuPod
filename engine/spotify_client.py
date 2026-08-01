"""
Spotify Web API client — powered by Spotipy.

Provides OAuth-authenticated access to the Spotify Web API for browsing
the user's library, searching, and controlling playback on Spotify Connect
devices.

Credentials are stored in ``files/spotify_token.json`` after the first
OAuth authorization, so the user only needs to authenticate once.

Usage
-----
    from engine.spotify_client import SpotifyClient

    client = SpotifyClient()
    if client.authenticate():
        playlists = client.get_playlists()
        ...
"""

import json
import os
import sys
import time
import tempfile
import logging
from typing import Optional

import spotipy
from spotipy.oauth2 import SpotifyOAuth

logger = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────────

# Users MUST set these environment variables (create an app at
# https://developer.spotify.com/dashboard to get your own):
#
#   export SPOTIPY_CLIENT_ID="your_client_id"
#   export SPOTIPY_CLIENT_SECRET="your_client_secret"
#   export SPOTIPY_REDIRECT_URI="http://127.0.0.1:8888/callback"
#
# Or create a .env file in the project root with:
#   SPOTIPY_CLIENT_ID=your_client_id
#   SPOTIPY_CLIENT_SECRET=your_client_secret
#   SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
#
# There are no hardcoded defaults — you must provide your own credentials.
DEFAULT_REDIRECT_URI = "http://127.0.0.1:8888/callback"


def _load_dotenv(path: str = ".env") -> None:
    """Load key=value pairs from a .env file into os.environ if not already set."""
    dotenv_path = os.path.join(os.path.dirname(__file__), "..", path)
    dotenv_path = os.path.normpath(dotenv_path)
    if not os.path.exists(dotenv_path):
        return
    try:
        with open(dotenv_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip("\"'")
                if key and val and key not in os.environ:
                    os.environ[key] = val
    except Exception:
        pass


# Load .env file at module import time so env vars are available
_load_dotenv()

TOKEN_PATH = os.path.join(os.path.dirname(__file__), "..", "files", "spotify_token.json")
TOKEN_PATH = os.path.normpath(TOKEN_PATH)

# Scopes for the Spotify API
SCOPES = (
    "playlist-read-private "
    "playlist-read-collaborative "
    "user-library-read "
    "user-follow-read "
    "user-read-playback-state "
    "user-modify-playback-state "
    "user-read-currently-playing "
    "streaming"
)

# ── Data helpers ─────────────────────────────────────────────────────────────

# Data structures matching the iPod UI's needs
# All API methods return simple dicts, not Spotipy objects, so the UI
# screens don't depend on the Spotipy library directly.


def _to_track_dict(item, cover_url: Optional[str] = None) -> dict:
    """Convert a Spotipy track item (from playlist/album/etc) to a uniform dict."""
    if item is None:
        return None
    track = item.get("track", item)  # unwrap playlist track wrapper
    if track is None:
        return None
    album = track.get("album", {})
    artists = track.get("artists", [])
    artist_name = artists[0].get("name", "Unknown") if artists else "Unknown"
    images = album.get("images", [])
    return {
        "id": track.get("id", ""),
        "uri": track.get("uri", ""),
        "title": track.get("name", "Unknown"),
        "artist": artist_name,
        "artist_id": artists[0].get("id", "") if artists else "",
        "album": album.get("name", "Unknown"),
        "album_id": album.get("id", ""),
        "track_number": track.get("track_number", 0),
        "duration_sec": round(track.get("duration_ms", 0) / 1000, 1),
        "cover_url": images[0].get("url") if images else cover_url,
        "cover_art_path": None,  # filled lazily by get_cover_art()
    }


def _to_album_dict(item) -> dict:
    """Convert a Spotipy saved-album or album item to a uniform dict."""
    if "album" in item:
        item = item["album"]
    images = item.get("images", [])
    artists = item.get("artists", [])
    return {
        "id": item.get("id", ""),
        "uri": item.get("uri", ""),
        "name": item.get("name", "Unknown"),
        "artist": artists[0].get("name", "Unknown") if artists else "Unknown",
        "artist_id": artists[0].get("id", "") if artists else "",
        "release_date": item.get("release_date", ""),
        "track_count": item.get("total_tracks", 0),
        "cover_url": images[0].get("url") if images else None,
        "cover_art_path": None,
    }


def _to_artist_dict(item) -> dict:
    """Convert a Spotipy artist item to a uniform dict."""
    images = item.get("images", [])
    return {
        "id": item.get("id", ""),
        "uri": item.get("uri", ""),
        "name": item.get("name", "Unknown"),
        "genres": item.get("genres", []),
        "followers": item.get("followers", {}).get("total", 0),
        "cover_url": images[0].get("url") if images else None,
        "cover_art_path": None,
    }


def _to_playlist_dict(item) -> dict:
    """Convert a Spotipy playlist item to a uniform dict."""
    images = item.get("images", [])
    return {
        "id": item.get("id", ""),
        "uri": item.get("uri", ""),
        "name": item.get("name", "Unknown"),
        "owner": item.get("owner", {}).get("display_name", "Unknown"),
        "track_count": item.get("tracks", {}).get("total", 0) if isinstance(item.get("tracks"), dict) else len(item.get("tracks", [])),
        "cover_url": images[0].get("url") if images else None,
        "cover_art_path": None,
    }


# ── Client singleton ─────────────────────────────────────────────────────────

_client_instance = None


def get_client():
    """Get or create the global SpotifyClient singleton."""
    global _client_instance
    if _client_instance is None:
        _client_instance = SpotifyClient()
    return _client_instance


class SpotifyClient:
    """Spotify Web API client wrapping Spotipy.

    Manages OAuth authentication and provides methods for browsing the
    user's library, searching, and controlling playback on Spotify Connect
    devices.

    Typical usage:

        client = SpotifyClient()
        if not client.authenticate():
            print("Need to authenticate with Spotify")
            # OAuth flow is triggered automatically
        playlists = client.get_playlists()
        tracks = client.get_playlist_tracks(playlists[0]["id"])
    """

    def __init__(self, client_id: Optional[str] = None,
                 client_secret: Optional[str] = None,
                 redirect_uri: Optional[str] = None):
        self._client_id = client_id or os.environ.get("SPOTIPY_CLIENT_ID")
        self._client_secret = client_secret or os.environ.get("SPOTIPY_CLIENT_SECRET")
        self._redirect_uri = redirect_uri or os.environ.get("SPOTIPY_REDIRECT_URI", DEFAULT_REDIRECT_URI)
        self._sp: Optional[spotipy.Spotify] = None
        self._auth_manager: Optional[SpotifyOAuth] = None
        self._username: Optional[str] = None
        self._authenticated = False
        self._last_playback_poll = 0
        self._cached_playback = None
        self._cover_cache_dir = os.path.join(tempfile.gettempdir(), "nupod_spotify_covers")
        os.makedirs(self._cover_cache_dir, exist_ok=True)

    # ── Authentication ──────────────────────────────────────────────────────

    def authenticate(self) -> bool:
        """Run the OAuth flow. Returns True if authentication succeeded.

        On first run, opens a browser to the Spotify authorization page.
        Subsequent runs reuse the stored token.

        You must set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET environment
        variables before calling this method. Get them from:
        https://developer.spotify.com/dashboard
        """
        # Validate credentials are configured
        if not self._client_id or not self._client_secret:
            logger.error("Spotify credentials not configured")
            print("\n" + "=" * 60, file=sys.stderr)
            print("  Spotify credentials not configured!", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            print("  Create a .env file in the project root with:\n", file=sys.stderr)
            print("    SPOTIPY_CLIENT_ID=your_client_id", file=sys.stderr)
            print("    SPOTIPY_CLIENT_SECRET=your_client_secret", file=sys.stderr)
            print("    SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback\n", file=sys.stderr)
            print("  Or set environment variables:\n", file=sys.stderr)
            print("    export SPOTIPY_CLIENT_ID='your_client_id'", file=sys.stderr)
            print("    export SPOTIPY_CLIENT_SECRET='your_client_secret'", file=sys.stderr)
            print("\n  Get credentials from: https://developer.spotify.com/dashboard", file=sys.stderr)
            print("=" * 60 + "\n", file=sys.stderr)
            return False

        try:
            self._auth_manager = SpotifyOAuth(
                client_id=self._client_id,
                client_secret=self._client_secret,
                redirect_uri=self._redirect_uri,
                scope=SCOPES,
                cache_path=TOKEN_PATH,
                open_browser=False,
            )
            token = self._auth_manager.get_cached_token()
            if token is None:
                logger.info("No cached token — starting OAuth flow")
                # Prints the authorization URL to the terminal and waits
                # for the user to paste the redirect URL back.
                print("\n" + "=" * 60)
                print("  Spotify Authorization Required")
                print("=" * 60)
                token = self._auth_manager.get_access_token(as_dict=False)
                if token is None:
                    logger.error("OAuth flow failed — no token returned")
                    return False
            self._sp = spotipy.Spotify(auth_manager=self._auth_manager)
            user = self._sp.current_user()
            self._username = user.get("display_name", user.get("id", "unknown"))
            self._authenticated = True
            logger.info("Authenticated as %s", self._username)
            print(f"[spotify] Authenticated as {self._username}")
            return True
        except Exception as e:
            logger.error("Authentication failed: %s", e)
            self._authenticated = False
            return False

    def is_authenticated(self) -> bool:
        return self._authenticated and self._sp is not None

    def get_username(self) -> str:
        return self._username or "Unknown"

    def get_auth_url(self) -> Optional[str]:
        """Get the OAuth authorization URL for manual browser flow."""
        if self._auth_manager is None:
            self._auth_manager = SpotifyOAuth(
                client_id=self._client_id,
                client_secret=self._client_secret,
                redirect_uri=self._redirect_uri,
                scope=SCOPES,
                cache_path=TOKEN_PATH,
                open_browser=False,
            )
        return self._auth_manager.get_authorize_url()

    def authenticate_with_code(self, code: str) -> bool:
        """Complete OAuth with an authorization code (for manual flow)."""
        try:
            if self._auth_manager is None:
                self._auth_manager = SpotifyOAuth(
                    client_id=self._client_id,
                    client_secret=self._client_secret,
                    redirect_uri=self._redirect_uri,
                    scope=SCOPES,
                    cache_path=TOKEN_PATH,
                    open_browser=False,
                )
            token = self._auth_manager.get_access_token(code, as_dict=False)
            self._sp = spotipy.Spotify(auth_manager=self._auth_manager)
            user = self._sp.current_user()
            self._username = user.get("display_name", user.get("id", "unknown"))
            self._authenticated = True
            return True
        except Exception as e:
            logger.error("Auth with code failed: %s", e)
            return False

    # ── Library: Playlists ──────────────────────────────────────────────────

    def get_playlists(self, limit=50) -> list[dict]:
        """Get the user's Spotify playlists."""
        if not self._check_auth():
            return []
        try:
            results = self._sp.current_user_playlists(limit=limit)
            return [_to_playlist_dict(item) for item in results.get("items", [])]
        except Exception as e:
            logger.error("get_playlists failed: %s", e)
            return []

    def get_playlist_tracks(self, playlist_id: str, limit=100) -> list[dict]:
        """Get tracks in a playlist."""
        if not self._check_auth():
            return []
        try:
            results = self._sp.playlist_tracks(playlist_id, limit=limit)
            return [_to_track_dict(item) for item in results.get("items", []) if _to_track_dict(item) is not None]
        except Exception as e:
            logger.error("get_playlist_tracks failed: %s", e)
            return []

    # ── Library: Albums ─────────────────────────────────────────────────────

    def get_saved_albums(self, limit=50) -> list[dict]:
        """Get the user's saved albums."""
        if not self._check_auth():
            return []
        try:
            results = self._sp.current_user_saved_albums(limit=limit)
            return [_to_album_dict(item) for item in results.get("items", [])]
        except Exception as e:
            logger.error("get_saved_albums failed: %s", e)
            return []

    def get_album_tracks(self, album_id: str, limit=50) -> list[dict]:
        """Get tracks in an album."""
        if not self._check_auth():
            return []
        try:
            results = self._sp.album_tracks(album_id, limit=limit)
            items = results.get("items", [])
            # Get album metadata for cover_url
            album = self._sp.album(album_id)
            cover_url = None
            if album and "images" in album:
                images = album.get("images", [])
                cover_url = images[0].get("url") if images else None
            return [_to_track_dict({"track": t}, cover_url=cover_url) for t in items if t is not None]
        except Exception as e:
            logger.error("get_album_tracks failed: %s", e)
            return []

    # ── Library: Artists ────────────────────────────────────────────────────

    def get_followed_artists(self, limit=50) -> list[dict]:
        """Get the user's followed artists."""
        if not self._check_auth():
            return []
        try:
            results = self._sp.current_user_followed_artists(limit=limit)
            items = results.get("artists", {}).get("items", [])
            return [_to_artist_dict(item) for item in items]
        except Exception as e:
            logger.error("get_followed_artists failed: %s", e)
            return []

    def get_artist_albums(self, artist_id: str, limit=50) -> list[dict]:
        """Get albums by an artist."""
        if not self._check_auth():
            return []
        try:
            results = self._sp.artist_albums(artist_id, limit=limit, album_type="album,single")
            return [_to_album_dict(item) for item in results.get("items", [])]
        except Exception as e:
            logger.error("get_artist_albums failed: %s", e)
            return []

    # ── Search ──────────────────────────────────────────────────────────────

    def search(self, query: str, search_type="track", limit=10) -> list[dict]:
        """Search Spotify.

        Args:
            query: Search query string.
            search_type: One of "track", "album", "artist", "playlist".
            limit: Max results (max 10 per Spotify API).

        Returns:
            List of matching items in the appropriate dict format.
        """
        if not self._check_auth():
            return []
        try:
            results = self._sp.search(q=query, type=search_type, limit=limit)
            key = search_type + "s"  # spotipy returns "tracks", "albums", etc.
            items = results.get(key, {}).get("items", [])
            if search_type == "track":
                return [_to_track_dict({"track": t}) for t in items if t is not None]
            elif search_type == "album":
                return [_to_album_dict(t) for t in items]
            elif search_type == "artist":
                return [_to_artist_dict(t) for t in items]
            elif search_type == "playlist":
                return [_to_playlist_dict(t) for t in items]
            return []
        except Exception as e:
            logger.error("search failed: %s", e)
            return []

    # ── Playback Control ────────────────────────────────────────────────────

    def get_devices(self) -> list[dict]:
        """Get available Spotify Connect devices."""
        if not self._check_auth():
            return []
        try:
            results = self._sp.devices()
            return results.get("devices", [])
        except Exception as e:
            logger.error("get_devices failed: %s", e)
            return []

    def start_playback(self, device_id: str, context_uri: Optional[str] = None,
                       uris: Optional[list[str]] = None,
                       offset: Optional[dict] = None) -> bool:
        """Start playback on a Spotify Connect device.

        Args:
            device_id: Target device ID.
            context_uri: Album/playlist URI for context playback.
            uris: List of track URIs for track playback.
            offset: {"position": N} or {"uri": "..."} for offset within context.

        Returns:
            True if successful.
        """
        if not self._check_auth():
            return False
        try:
            self._sp.start_playback(
                device_id=device_id,
                context_uri=context_uri,
                uris=uris,
                offset=offset,
            )
            return True
        except Exception as e:
            logger.error("start_playback failed: %s", e)
            return False

    def pause_playback(self, device_id: Optional[str] = None) -> bool:
        """Pause playback."""
        if not self._check_auth():
            return False
        try:
            self._sp.pause_playback(device_id=device_id)
            return True
        except Exception as e:
            logger.error("pause_playback failed: %s", e)
            return False

    def next_track(self, device_id: Optional[str] = None) -> bool:
        """Skip to next track."""
        if not self._check_auth():
            return False
        try:
            self._sp.next_track(device_id=device_id)
            return True
        except Exception as e:
            return False

    def previous_track(self, device_id: Optional[str] = None) -> bool:
        """Skip to previous track."""
        if not self._check_auth():
            return False
        try:
            self._sp.previous_track(device_id=device_id)
            return True
        except Exception as e:
            return False

    def seek_track(self, position_ms: int, device_id: Optional[str] = None) -> bool:
        """Seek to position in milliseconds."""
        if not self._check_auth():
            return False
        try:
            self._sp.seek_track(position_ms, device_id=device_id)
            return True
        except Exception as e:
            return False

    def transfer_playback(self, device_id: str, play: bool = True) -> bool:
        """Transfer playback to a specific device."""
        if not self._check_auth():
            return False
        try:
            self._sp.transfer_playback(device_id, play)
            return True
        except Exception as e:
            logger.error("transfer_playback failed: %s", e)
            return False

    # ── Current Playback State ──────────────────────────────────────────────

    def get_current_playback(self) -> Optional[dict]:
        """Get the current playback state.

        Returns a dict with keys:
            is_playing, track, artist, album, album_cover_url,
            progress_ms, duration_ms, device_id, shuffle_state, repeat_state

        Returns None if nothing is playing.
        """
        if not self._check_auth():
            return None
        try:
            now = time.time()
            # Cache for 1 second to avoid hitting rate limits
            if now - self._last_playback_poll > 1.0:
                result = self._sp.current_playback()
                self._last_playback_poll = now
                self._cached_playback = result
            else:
                result = self._cached_playback

            if result is None:
                return None

            item = result.get("item")
            if item is None:
                return None

            album = item.get("album", {})
            artists = item.get("artists", [])
            images = album.get("images", [])

            return {
                "is_playing": result.get("is_playing", False),
                "track": item.get("name", "Unknown"),
                "artist": artists[0].get("name", "Unknown") if artists else "Unknown",
                "album": album.get("name", "Unknown"),
                "album_cover_url": images[0].get("url") if images else None,
                "progress_ms": result.get("progress_ms", 0),
                "duration_ms": item.get("duration_ms", 0),
                "device_id": (result.get("device") or {}).get("id", ""),
                "device_name": (result.get("device") or {}).get("name", ""),
                "shuffle_state": result.get("shuffle_state", False),
                "repeat_state": result.get("repeat_state", "off"),
                "context_uri": result.get("context", {}).get("uri", "") if result.get("context") else "",
            }
        except Exception as e:
            logger.error("get_current_playback failed: %s", e)
            return None

    # ── Cover art ───────────────────────────────────────────────────────────

    def get_cover_art(self, url: str, track_id: str = "") -> Optional[str]:
        """Download a cover art image from a URL and cache it locally.

        Returns the local file path, or None on failure.
        """
        if not url:
            return None
        cache_key = track_id or url.split("/")[-1].split("?")[0]
        cache_path = os.path.join(self._cover_cache_dir, f"{cache_key}.jpg")
        if os.path.exists(cache_path):
            return cache_path
        try:
            import requests
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                with open(cache_path, "wb") as f:
                    f.write(resp.content)
                return cache_path
        except Exception as e:
            logger.error("get_cover_art failed: %s", e)
        return None

    # ── Internal ────────────────────────────────────────────────────────────

    def _check_auth(self) -> bool:
        """Ensure we're authenticated; attempt re-auth if needed."""
        if not self._authenticated:
            return self.authenticate()
        return True
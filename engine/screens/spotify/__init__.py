"""Spotify screens — browse the user's Spotify library via the Web API.

All screens rely on the SpotifyClient singleton from engine.spotify_client.
The Spotify Connect receiver is managed by engine.spotify_connect.

These screens are mutually exclusive with the local music screens — when
you play a Spotify track, the audio system switches to Spotify mode.
"""

from hardware import audio
from engine.spotify_client import get_client
from engine.spotify_connect import get_connect


def play_spotify_track(uris: list, start_index: int = 0) -> bool:
    """Start playback on an available Spotify Connect device.

    Tries our own Connect receiver first (if a client has connected).
    Falls back to any other available device (phone, computer, etc.).
    Once the nuPod Connect device is active (play to it from your
    Spotify app), the UI will use it automatically.

    Returns True if playback was started successfully.
    """
    if not uris:
        return False

    client = get_client()
    if not client._check_auth():
        return False

    audio.set_spotify_mode(True)

    # Try our own Connect receiver — only if a client has connected
    # (has_session means the ZeroconfServer has an active session)
    connect = get_connect()
    if connect.is_running() and connect.has_session():
        device_id = connect.get_device_id()
        offset = {"position": start_index}
        if len(uris) > 1:
            return client.start_playback(
                device_id=device_id, uris=uris, offset=offset
            )
        else:
            return client.start_playback(device_id=device_id, uris=uris)

    # No Connect session yet — device is still being discovered.
    # Fall back to any available device (phone, computer, etc.)
    devices = client.get_devices()
    if devices:
        active = [d for d in devices if d.get("is_active")] or devices
        device_id = active[0].get("id")
        if device_id:
            offset = {"position": start_index}
            if len(uris) > 1:
                return client.start_playback(
                    device_id=device_id, uris=uris, offset=offset
                )
            else:
                return client.start_playback(device_id=device_id, uris=uris)

    # Try playback without specifying a device (uses last active device)
    try:
        offset = {"position": start_index}
        if len(uris) > 1:
            return client.start_playback(uris=uris, offset=offset)
        else:
            return client.start_playback(uris=uris)
    except Exception:
        pass

    return False


from .playlists import SpotifyPlaylistsScreen
from .albums import SpotifyAlbumsScreen
from .artists import SpotifyArtistsScreen
from .search import SpotifySearchScreen

__all__ = [
    "SpotifyPlaylistsScreen",
    "SpotifyAlbumsScreen",
    "SpotifyArtistsScreen",
    "SpotifySearchScreen",
    "play_spotify_track",
]
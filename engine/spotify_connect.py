"""
Spotify Connect receiver — powered by librespot-python.

Makes the device appear as a Spotify Connect speaker on the local network,
so users can play to it from their phone, computer, or other Spotify client.

Uses librespot-python's built-in ZeroconfServer to broadcast the device
and handle incoming Spotify audio streams.

The receiver runs in a background thread so it doesn't block the main UI loop.
"""

import logging
import os
import threading
import time
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "..", "files", "spotify_credentials.json")
CREDENTIALS_PATH = os.path.normpath(CREDENTIALS_PATH)

DEVICE_NAME = "nuPod"
DEVICE_ID = "nupod-" + os.uname().nodename if hasattr(os, "uname") else "nupod-001"
PREFERRED_LOCALE = "en"

# ── Singleton ─────────────────────────────────────────────────────────────────

_connect_instance = None


def get_connect():
    """Get or create the global SpotifyConnect singleton."""
    global _connect_instance
    if _connect_instance is None:
        _connect_instance = SpotifyConnect()
    return _connect_instance


class SpotifyConnect:
    """Manages a librespot Spotify Connect receiver.

    Typical usage:

        connect = SpotifyConnect()
        connect.start()
        ...
        device_id = connect.get_device_id()  # use with Spotipy
        ...
        connect.stop()
    """

    def __init__(self, device_name: str = DEVICE_NAME,
                 device_id: str = DEVICE_ID):
        self._device_name = device_name
        self._device_id = device_id
        self._session = None
        self._zeroconf_server = None
        self._thread = None
        self._running = False
        self._ready = False
        self._playback_listeners: list[Callable] = []
        self._error: Optional[str] = None

    # ── Public API ──────────────────────────────────────────────────────────

    def start(self) -> bool:
        """Start the Spotify Connect receiver in a background thread.

        Returns True if the receiver started or is starting (including
        if OAuth authentication is needed — the user will see a URL
        printed to the terminal).

        Returns False only if a critical error occurred.
        """
        if self._running:
            return True

        self._error = None
        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name="spotify-connect")
        self._thread.start()

        # Wait for initialization (OAuth may take a while if user interaction needed)
        # Check every 100ms for up to 30 seconds
        for _ in range(300):
            if self._ready or self._error:
                break
            time.sleep(0.1)

        if self._error:
            logger.error("Spotify Connect: %s", self._error)
            return False
        if self._ready:
            logger.info("Spotify Connect receiver ready: %s", self._device_name)
            return True
        # Still starting (probably waiting for OAuth) — that's fine
        logger.info("Spotify Connect receiver starting (OAuth may be pending)")
        return True

    def stop(self):
        """Stop the Spotify Connect receiver."""
        self._running = False
        if self._zeroconf_server is not None:
            try:
                self._zeroconf_server.close()
            except Exception:
                pass
            self._zeroconf_server = None
        if self._session is not None:
            try:
                self._session.close()
            except Exception:
                pass
            self._session = None
        self._ready = False
        self._thread = None
        logger.info("Spotify Connect receiver stopped")

    def is_running(self) -> bool:
        return self._running and self._ready

    def has_session(self) -> bool:
        """Check if the ZeroconfServer has an active session (a Spotify
        client has connected to this device)."""
        if self._zeroconf_server is not None:
            try:
                return self._zeroconf_server.has_valid_session()
            except Exception:
                pass
        return False

    def get_device_id(self) -> str:
        return self._device_id

    def get_device_name(self) -> str:
        return self._device_name

    def get_session(self):
        """Get the librespot Session object (for advanced use)."""
        return self._session

    def get_error(self) -> Optional[str]:
        return self._error

    def add_playback_listener(self, callback: Callable):
        """Register a callback that fires when playback state changes.

        The callback receives no arguments — call get_current_playback()
        on the SpotifyClient to get the current state.
        """
        if callback not in self._playback_listeners:
            self._playback_listeners.append(callback)

    def remove_playback_listener(self, callback: Callable):
        if callback in self._playback_listeners:
            self._playback_listeners.remove(callback)

    # ── Internal: authentication ────────────────────────────────────────────

    def _authenticate(self):
        """Authenticate with Spotify via librespot-python.

        Uses the OAuth flow which:
          1. Checks for stored credentials first (auto-reuse)
          2. If none found, starts the OAuth PKCE flow (opens browser)
          3. Saves credentials for next time

        Uses a custom configuration so credentials are stored at
        ``files/spotify_credentials.json``.

        Note: librespot requires a Spotify Premium account for audio
        streaming via the Connect protocol.
        """
        import librespot.core as core

        # Create a custom config pointing to our credentials file
        conf = core.Session.Configuration.Builder() \
            .set_store_credentials(True) \
            .set_stored_credential_file(CREDENTIALS_PATH) \
            .set_cache_enabled(True) \
            .set_cache_dir(os.path.join(os.path.dirname(CREDENTIALS_PATH), ".spotify_cache")) \
            .set_do_cache_clean_up(True) \
            .set_retry_on_chunk_error(True) \
            .build()

        builder = core.Session.Builder(conf)
        builder.set_device_name(self._device_name)
        builder.set_device_id(self._device_id)
        builder.set_device_type(core.Connect.DeviceType.SPEAKER)
        builder.set_preferred_locale(PREFERRED_LOCALE)

        # Check for stored credentials first (fast path)
        if os.path.exists(conf.stored_credentials_file):
            try:
                logger.info("Loading stored Spotify Connect credentials")
                session = builder.stored_file(None).create()
                logger.info("Spotify Connect authenticated (stored credentials)")
                return session
            except Exception as e:
                logger.warning("Stored credentials failed: %s", e)
                # Remove corrupted file so OAuth can retry
                try:
                    os.remove(conf.stored_credentials_file)
                except Exception:
                    pass

        # No stored credentials — offer OAuth flow
        # (Requires user to open a browser and authorize)
        logger.info("No stored Spotify Connect credentials")
        logger.info("Starting OAuth flow — a browser URL will be printed")
        try:
            session = builder.oauth(self._oauth_url_callback).create()
            logger.info("Spotify Connect authenticated via OAuth!")
            return session
        except Exception as e:
            logger.warning("Spotify Connect OAuth failed: %s", e)
            return None

    @staticmethod
    def _oauth_url_callback(url: str):
        """Called when the OAuth URL is ready — print it for the user."""
        print("\n" + "=" * 60)
        print("  Spotify Connect Authentication Required")
        print("=" * 60)
        print("  Open this URL in your browser to authorize nuPod")
        print("  as a Spotify Connect device:\n")
        print(f"  {url}\n")
        print("  (Requires a Spotify Premium account)")
        print("=" * 60 + "\n")

    def _save_credentials(self, session):
        """Save session credentials for future use."""
        try:
            creds = session.stored()
            os.makedirs(os.path.dirname(CREDENTIALS_PATH), exist_ok=True)
            with open(CREDENTIALS_PATH, "w") as f:
                f.write(creds)
            logger.info("Saved credentials to %s", CREDENTIALS_PATH)
        except Exception as e:
            logger.warning("Failed to save credentials: %s", e)

    # ── Internal: Zeroconf server ───────────────────────────────────────────

    def _run(self):
        """Main loop for the Connect receiver thread.

        The ZeroconfServer broadcasts the device on the local network via
        mDNS so that Spotify clients (phone, computer, etc.) can discover
        it and play to it. The ZeroconfServer handles authentication
        internally when a client connects — it creates a session from
        the client's auth blob.

        The device appears as a Connect target named "nuPod" in the Spotify
        app on the same network. Once a client has connected, the device
        is registered with the Spotify API and the UI can control playback.
        """
        import librespot.zeroconf as zc
        import librespot.core as core

        self._running = True

        try:
            # Build a configuration pointing to our credentials file
            conf = core.Session.Configuration.Builder() \
                .set_store_credentials(True) \
                .set_stored_credential_file(CREDENTIALS_PATH) \
                .set_cache_enabled(True) \
                .set_cache_dir(os.path.join(
                    os.path.dirname(CREDENTIALS_PATH), ".spotify_cache")) \
                .set_do_cache_clean_up(True) \
                .set_retry_on_chunk_error(True) \
                .build()

            # Start the ZeroconfServer — this broadcasts the device on
            # the local network. The session is created automatically
            # when a Spotify client connects to this device.
            inner = zc.ZeroconfServer.Inner(
                device_type=core.Connect.DeviceType.SPEAKER,
                device_name=self._device_name,
                device_id=self._device_id,
                preferred_locale=PREFERRED_LOCALE,
                conf=conf,
            )
            self._zeroconf_server = zc.ZeroconfServer(inner, listen_port=0)

            self._ready = True
            logger.info("Spotify Connect ready: %s (on network)", self._device_name)

            # Keep the thread alive (the ZeroconfServer runs its own
            # HTTP server for the Connect protocol internally).
            while self._running:
                time.sleep(2.0)

        except Exception as e:
            self._error = str(e)
            logger.error("Spotify Connect error: %s", e)
        finally:
            self._running = False
            self._ready = False
            if self._zeroconf_server is not None:
                try:
                    self._zeroconf_server.close()
                except Exception:
                    pass
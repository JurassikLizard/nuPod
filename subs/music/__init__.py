"""
Music subsystem — loading, playing, and controlling music playback.

This subsystem is the bridge between the on-disk music library in
``files/music/`` and the hardware abstraction layer (``hardware/audio``).

Usage::

    from subs.music import library, player

    # Scan the library (scans once, caches metadata)
    lib = library.Library()
    lib.scan()

    # Browse
    for artist in lib.artists:
        for album in artist.albums:
            for song in album.songs:
                print(song.title)

    # Play
    player.play(song)
    player.pause()
    player.resume()
    player.seek(30.0)
    player.stop()
"""

from . import config
from . import models
from . import library
from . import metadata
from . import player

__all__ = ["config", "models", "library", "metadata", "player"]
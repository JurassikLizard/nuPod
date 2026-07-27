"""Screen protocol and base class for leaf-node views.

Each screen is a full-screen view that replaces the menu when active.
Screens follow a simple lifecycle: on_enter → handle_input/render loop → on_exit.
"""

from ..input import InputEvent, ButtonPress, ScrollEvent, Button


class Screen:
    """Base class for all leaf-node screens.

    Subclasses should override render() and optionally handle_input(),
    on_enter(), and on_exit().
    """

    def on_enter(self):
        """Called when this screen becomes active (pushed onto stack)."""
        pass

    def on_exit(self):
        """Called when this screen is no longer active (popped from stack)."""
        pass

    def handle_input(self, event: InputEvent):
        """Handle an input event (ButtonPress or ScrollEvent).

        Return "back" to signal the screen should close and return to menu.
        Return True if the input was consumed, False if it should fall through.
        """
        return False

    def render(self, renderer, assets, theme, viewport):
        """Draw this screen. viewport is (x, y, w, h) for the rendering area."""
        pass


# ── import all screen classes so they can be imported from screens.* ────────

from .clock import ClockScreen
from .about import AboutScreen
from .now_playing import NowPlayingScreen
from .songs import SongsScreen
from .placeholder import PlaceholderScreen
from .playlists import PlaylistsScreen
from .artists import ArtistsScreen
from .albums import AlbumsScreen
from .genres import GenresScreen
from .composers import ComposersScreen
from .audiobooks import AudiobooksScreen
from .contacts import ContactsScreen
from .calendar import CalendarScreen
from .notes import NotesScreen
from .games import GamesScreen
from .eq import EQScreen

__all__ = [
    "Screen",
    "ClockScreen", "AboutScreen", "NowPlayingScreen", "SongsScreen",
    "BrowseScreen", "PlaceholderScreen",
    "PlaylistsScreen", "ArtistsScreen", "AlbumsScreen", "GenresScreen",
    "ComposersScreen", "AudiobooksScreen",
    "ContactsScreen", "CalendarScreen", "NotesScreen", "GamesScreen",
    "EQScreen",
]
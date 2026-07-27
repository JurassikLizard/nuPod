"""Menu tree definitions for the iPod classic UI.

Each function returns a list of MenuItems for its menu level.
The main menu is built by `build_main_menu()` which is called
from the main loop.
"""

from .menu import submenu, screen_item, action, toggle, enum_setting, value_setting
from .screens.now_playing import NowPlayingScreen
from .screens.about import AboutScreen
from .screens.clock import ClockScreen
from .screens.songs import SongsScreen
from .screens.browse import BrowseScreen
from .screens.placeholder import PlaceholderScreen
from .screens.playlists import PlaylistsScreen
from .screens.artists import ArtistsScreen
from .screens.albums import AlbumsScreen
from .screens.genres import GenresScreen
from .screens.composers import ComposersScreen
from .screens.audiobooks import AudiobooksScreen
from .screens.contacts import ContactsScreen
from .screens.calendar import CalendarScreen
from .screens.notes import NotesScreen
from .screens.games import GamesScreen
from .screens.eq import EQScreen


def placeholder_item(title, message="Not yet available"):
    """A screen item that shows a placeholder message."""
    return screen_item(title, type(
        title.replace(" ", "") + "Placeholder",
        (PlaceholderScreen,),
        {"__init__": lambda self, t=title, m=message: PlaceholderScreen.__init__(self, t, m)},
    ))


def build_main_menu(state, close_menu_fn, quit_fn=None):
    """Build the main menu tree. Call this each time the menu is opened
    so conditional items (Now Playing) reflect current state."""

    # ---- Music submenu ----------------------------------------------------

    music_sub = submenu("Music", [
        screen_item("Playlists", PlaylistsScreen),
        screen_item("Artists", ArtistsScreen),
        screen_item("Albums", AlbumsScreen),
        screen_item("Songs", SongsScreen),
        screen_item("Genres", GenresScreen),
        screen_item("Composers", ComposersScreen),
        screen_item("Audiobooks", AudiobooksScreen),
    ])

    # ---- Browse submenu ----------------------------------------------------

    browse_sub = submenu("Browse", [
        screen_item("Playlists", PlaylistsScreen),
        screen_item("Artists", ArtistsScreen),
        screen_item("Albums", AlbumsScreen),
        screen_item("Songs", type("BrowseSongs", (SongsScreen,), {})),
        screen_item("Genres", GenresScreen),
        screen_item("Composers", ComposersScreen),
        screen_item("Audiobooks", AudiobooksScreen),
    ])

    # ---- Extras submenu ----------------------------------------------------

    extras_sub = submenu("Extras", [
        screen_item("Contacts", ContactsScreen),
        screen_item("Calendar", CalendarScreen),
        screen_item("Notes", NotesScreen),
        screen_item("Clock", ClockScreen),
        screen_item("Games", GamesScreen),
    ])

    # ---- Settings submenu --------------------------------------------------

    def reset_all():
        from hardware.settings import reset_all_settings
        reset_all_settings()

    settings_sub = submenu("Settings", [
        screen_item("About", AboutScreen),

        # Backlight Timer (value adjust)
        value_setting(
            "Backlight Timer",
            lambda: state.backlight_timeout_s,
            lambda v: setattr(state, "backlight_timeout_s", v),
            5, 60, 5,
            formatter=lambda v: f"{v}s" if v > 0 else "Always On",
        ),

        # Clicker (toggle)
        toggle("Clicker", lambda: state.clicker_enabled, lambda v: setattr(state, "clicker_enabled", v)),

        # EQ (full-screen graphic equalizer)
        screen_item("EQ", EQScreen),

        # Shuffle (toggle)
        toggle("Shuffle", lambda: state.shuffle_enabled, lambda v: setattr(state, "shuffle_enabled", v)),

        # Repeat (enum)
        enum_setting(
            "Repeat", lambda: state.repeat_mode,
            lambda v: setattr(state, "repeat_mode", v),
            ["OFF", "ALL", "ONE", "AB", "SHUFFLE"],
        ),

        # Volume Limit (value adjust)
        value_setting(
            "Volume Limit",
            lambda: state.volume_limit,
            lambda v: setattr(state, "volume_limit", v),
            0, 100, 10,
            formatter=lambda v: f"{v}%",
        ),

        # Language (enum)
        enum_setting(
            "Language",
            lambda: state.language,
            lambda v: setattr(state, "language", v),
            ["English", "Spanish", "French", "German", "Japanese", "Chinese"],
        ),

        # Contrast (value adjust)
        value_setting(
            "Contrast",
            lambda: state.contrast,
            lambda v: setattr(state, "contrast", v),
            0, 100, 5,
            formatter=lambda v: f"{v}%",
        ),

        # Sound Check (toggle)
        toggle("Sound Check", lambda: state.sound_check, lambda v: setattr(state, "sound_check", v)),

        # Backlight (enum)
        enum_setting(
            "Backlight",
            lambda: state.backlight_mode,
            lambda v: setattr(state, "backlight_mode", v),
            ["ON", "OFF", "TIMER"],
        ),

        # Main Menu (customize)
        placeholder_item("Main Menu", "Customize main menu items"),

        # Reset All Settings
        action("Reset All Settings", reset_all),
    ])

    # ---- Root menu items ---------------------------------------------------

    items = []

    # Now Playing — only when a song is actually playing
    if state.audio_active:
        items.append(screen_item("Now Playing", NowPlayingScreen))

    items.append(music_sub)
    items.append(action("Shuffle Songs", lambda: setattr(state, "shuffle_enabled", True)))
    items.append(browse_sub)
    items.append(extras_sub)
    items.append(settings_sub)

    if quit_fn:
        items.append(action("Quit", quit_fn))

    return items
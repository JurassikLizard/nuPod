"""
Music/Playlists screen — browse and select playlists.

Each playlist is a named collection of songs. Selecting one shows the songs
in that playlist, and selecting a song starts playback.
"""

from . import Screen, ScrollEvent, ButtonPress, Button
from .songs import STUB_SONGS
from hardware import audio
import sdl2


# Stub playlists
STUB_PLAYLISTS = [
    {"name": "Favorites",       "songs": [0, 3, 7, 11, 15, 19]},
    {"name": "Road Trip",       "songs": [2, 5, 8, 10, 14, 17, 20]},
    {"name": "Workout Mix",     "songs": [1, 4, 6, 9, 12, 16, 18]},
    {"name": "Chill Vibes",     "songs": [3, 7, 11, 14, 17]},
    {"name": "Late Night",      "songs": [0, 2, 5, 8, 13, 19]},
    {"name": "Morning Coffee",  "songs": [1, 6, 10, 15, 18]},
    {"name": "Weekend Party",   "songs": [4, 9, 12, 16, 20]},
    {"name": "Focus",           "songs": [0, 3, 7, 11, 14, 17, 20]},
    {"name": "Throwbacks",      "songs": [1, 2, 4, 8, 13, 15, 19]},
    {"name": "New Discoveries", "songs": [5, 6, 9, 10, 12, 16, 18]},
]


class PlaylistsScreen(Screen):
    """Music > Playlists: list of playlists with drill-down to songs."""

    def __init__(self):
        self._stack = []  # navigation stack
        self._playlists = STUB_PLAYLISTS
        self._selected = 0
        self._scroll_offset = 0

    def handle_input(self, event):
        if isinstance(event, ScrollEvent):
            items = self._stack[-1]["songs"] if self._stack else self._playlists
            if event.direction < 0:  # CCW = up
                self._selected = max(0, self._selected - 1)
            else:  # CW = down
                self._selected = min(len(items) - 1, self._selected + 1)
            return True
        if isinstance(event, ButtonPress):
            btn = event.button
            if btn == Button.UP:
                if self._stack:
                    self._stack.pop()
                    self._selected = 0
                    self._scroll_offset = 0
                    return True
                return "back"
            if btn == Button.CENTER:
                items = self._stack[-1]["songs"] if self._stack else self._playlists
                if not self._stack:
                    idx = self._selected
                    playlist = self._playlists[idx]
                    songs = [(i, STUB_SONGS[i]) for i in playlist["songs"]]
                    self._stack.append({"name": playlist["name"], "songs": songs})
                    self._selected = 0
                    self._scroll_offset = 0
                else:
                    _, song_name = self._stack[-1]["songs"][self._selected]
                    display = song_name.split(" - ", 1)[1] if " - " in song_name else song_name
                    audio.set_title(display)
                    audio.set_artist("Unknown Artist")
                    audio.set_album("Unknown Album")
                    audio.set_elapsed_sec(0.0)
                    audio.set_play_state("PLAYING")
            return True
        return False

    def render(self, renderer, assets, theme, viewport):
        vx, vy, vw, vh = viewport
        bg = self._hex_rgb(theme.get("colors", {}).get("background", "FFFFFF"))
        sdl2.SDL_SetRenderDrawColor(renderer, *bg, 255)
        sdl2.SDL_RenderFillRect(renderer, sdl2.SDL_Rect(vx, vy, vw, vh))

        text_color = self._hex_rgb(theme.get("colors", {}).get("foreground", "000000"))
        sel_color = self._hex_rgb(theme.get("colors", {}).get("selector_text", "FFFFFF"))
        sel_start = self._hex_rgb(theme.get("colors", {}).get("selector_start", "5C9AE7"))
        sel_end = self._hex_rgb(theme.get("colors", {}).get("selector_end", "3268D2"))
        secondary = self._hex_rgb(theme.get("colors", {}).get("secondary_text", "999999"))

        # Header / breadcrumb
        if self._stack:
            header = self._stack[-1]["name"]
            htex, hw, hh = assets.render_text(header, secondary)
            if htex:
                dst = sdl2.SDL_Rect(vx + 4, vy + 2, hw, hh)
                sdl2.SDL_RenderCopy(renderer, htex, None, dst)
                sdl2.SDL_DestroyTexture(htex)

        items = self._stack[-1]["songs"] if self._stack else self._playlists
        row_h = 18
        list_y = vy + (14 if self._stack else 2)
        list_h = vh - (list_y - vy)
        visible = max(1, list_h // row_h)

        if self._selected < self._scroll_offset:
            self._scroll_offset = self._selected
        elif self._selected >= self._scroll_offset + visible:
            self._scroll_offset = self._selected - visible + 1

        y = list_y
        end = min(len(items), self._scroll_offset + visible)
        for i in range(self._scroll_offset, end):
            sel = i == self._selected
            if sel:
                self._draw_gradient(renderer, vx, y, vw, row_h, sel_start, sel_end)
            color = sel_color if sel else text_color

            if self._stack:
                idx, sname = items[i]
                num = sname.split(" - ", 1)[0] if " - " in sname else str(idx + 1)
                label = sname.split(" - ", 1)[1] if " - " in sname else sname
                display = f"{num}. {label}"
            else:
                display = items[i]["name"]
                count = len(items[i]["songs"])
                display = f"{display} ({count})"

            tex, tw, th = assets.render_text(display, color)
            if tex:
                dst = sdl2.SDL_Rect(vx + 4, y + (row_h - th) // 2, tw, th)
                sdl2.SDL_RenderCopy(renderer, tex, None, dst)
                sdl2.SDL_DestroyTexture(tex)
            y += row_h

    @staticmethod
    def _draw_gradient(renderer, x, y, w, h, c1, c2, bands=8):
        for b in range(bands):
            t = b / max(1, bands - 1)
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            bl = int(c1[2] + (c2[2] - c1[2]) * t)
            band_h = max(1, h // bands)
            sdl2.SDL_SetRenderDrawColor(renderer, r, g, bl, 255)
            sdl2.SDL_RenderFillRect(renderer, sdl2.SDL_Rect(x, y + b * band_h, w, band_h + 1))

    @staticmethod
    def _hex_rgb(h):
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
"""
Music/Albums screen — browse music by album.

Selecting an album shows its songs, selecting a song starts playback.
"""

from . import Screen, ScrollEvent, ButtonPress, Button
from .songs import STUB_SONGS
from hardware import audio
import sdl2


# Stub albums
STUB_ALBUMS = [
    {"name": "Summer Nights",       "artist": "The Midnight Echo", "year": 2024, "songs": [0, 1, 2, 3, 4]},
    {"name": "Electric Dreams",     "artist": "The Midnight Echo", "year": 2025, "songs": [5, 6, 7, 8, 9]},
    {"name": "Ocean Blues",         "artist": "Luna Wave",        "year": 2024, "songs": [10, 11, 12, 13]},
    {"name": "City Lights",         "artist": "Neon Pulse",       "year": 2023, "songs": [14, 15, 16]},
    {"name": "After Dark",          "artist": "Neon Pulse",       "year": 2025, "songs": [17, 18]},
    {"name": "Winter Garden",       "artist": "Crystal Falls",    "year": 2024, "songs": [19, 20]},
    {"name": "Golden Hour",         "artist": "The Velvet Sunset","year": 2023, "songs": [0, 2, 4, 6, 8]},
    {"name": "Dusk Til Dawn",       "artist": "The Velvet Sunset","year": 2025, "songs": [10, 12, 14]},
    {"name": "Midnight Chronicles", "artist": "Various Artists",  "year": 2025, "songs": [1, 3, 5, 7, 9, 11, 13]},
    {"name": "Acoustic Sessions",   "artist": "Various Artists",  "year": 2024, "songs": [2, 6, 10, 14, 18]},
]


class AlbumsScreen(Screen):
    """Music > Albums: album list with drill-down to songs."""

    def __init__(self):
        self._stack = []
        self._selected = 0
        self._scroll_offset = 0

    def handle_input(self, event):
        if isinstance(event, ScrollEvent):
            items = self._current_items()
            if event.direction < 0:
                self._selected = max(0, self._selected - 1)
            else:
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
                if not self._stack:
                    album = STUB_ALBUMS[self._selected]
                    songs = [(i, STUB_SONGS[i]) for i in album["songs"]]
                    self._stack.append({"label": album["name"], "items": songs})
                    self._selected = 0
                    self._scroll_offset = 0
                else:
                    _, song_name = self._current_items()[self._selected]
                    display = song_name.split(" - ", 1)[1] if " - " in song_name else song_name
                    album_name = self._stack[0]["label"]
                    album_artist = next((a["artist"] for a in STUB_ALBUMS if a["name"] == album_name), "Unknown Artist")
                    audio.set_title(display)
                    audio.set_artist(album_artist)
                    audio.set_album(album_name)
                    audio.set_elapsed_sec(0.0)
                    audio.set_play_state("PLAYING")
            return True
        return False

    def _current_items(self):
        if not self._stack:
            return STUB_ALBUMS
        return self._stack[-1]["items"]

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

        if self._stack:
            ltex, lw, lh = assets.render_text(self._stack[-1]["label"], secondary)
            if ltex:
                dst = sdl2.SDL_Rect(vx + 4, vy + 2, lw, lh)
                sdl2.SDL_RenderCopy(renderer, ltex, None, dst)
                sdl2.SDL_DestroyTexture(ltex)

        items = self._current_items()
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

            if not self._stack:
                display = items[i]["name"]
                tex, tw, th = assets.render_text(display, color)
            else:
                _, song_name = items[i]
                num = song_name.split(" - ", 1)[0] if " - " in song_name else str(items[i][0] + 1)
                label = song_name.split(" - ", 1)[1] if " - " in song_name else song_name
                display = f"{num}. {label}"
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
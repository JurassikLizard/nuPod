"""
Music/Artists screen — browse music alphabetically by artist.

Selecting an artist shows their albums, and selecting an album shows songs.
Selecting a song starts playback.
"""

from . import Screen, ScrollEvent, ButtonPress, Button
from .songs import STUB_SONGS
from hardware import audio
import sdl2


# Stub artists with albums and song indices
STUB_ARTISTS = [
    {
        "name": "The Midnight Echo",
        "albums": [
            {"name": "Summer Nights", "songs": [0, 1, 2, 3, 4]},
            {"name": "Electric Dreams", "songs": [5, 6, 7, 8, 9]},
        ],
    },
    {
        "name": "Luna Wave",
        "albums": [
            {"name": "Ocean Blues", "songs": [10, 11, 12, 13]},
        ],
    },
    {
        "name": "Neon Pulse",
        "albums": [
            {"name": "City Lights", "songs": [14, 15, 16]},
            {"name": "After Dark", "songs": [17, 18]},
        ],
    },
    {
        "name": "Crystal Falls",
        "albums": [
            {"name": "Winter Garden", "songs": [19, 20]},
        ],
    },
    {
        "name": "The Velvet Sunset",
        "albums": [
            {"name": "Golden Hour", "songs": [0, 2, 4, 6, 8]},
            {"name": "Dusk Til Dawn", "songs": [10, 12, 14]},
        ],
    },
]


class ArtistsScreen(Screen):
    """Music > Artists: alphabetical artist list with drill-down."""

    def __init__(self):
        self._stack = []   # list of {"label": str, "items": list}
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
                level = len(self._stack)
                if level == 0:
                    artist = STUB_ARTISTS[self._selected]
                    self._stack.append({"label": artist["name"], "items": artist["albums"]})
                    self._selected = 0
                    self._scroll_offset = 0
                elif level == 1:
                    album = self._current_items()[self._selected]
                    self._stack.append({"label": album["name"], "items": album["songs"]})
                    self._selected = 0
                    self._scroll_offset = 0
                else:
                    song_idx = self._current_items()[self._selected]
                    sname = STUB_SONGS[song_idx] if song_idx < len(STUB_SONGS) else f"Track {song_idx + 1}"
                    display = sname.split(" - ", 1)[1] if " - " in sname else sname
                    audio.set_title(display)
                    audio.set_artist(self._stack[0]["label"])
                    audio.set_album(self._stack[1]["label"])
                    audio.set_elapsed_sec(0.0)
                    audio.set_play_state("PLAYING")
            return True
        return False

    def _current_items(self):
        if not self._stack:
            return STUB_ARTISTS
        return self._stack[-1]["items"]

    def _current_label(self):
        if not self._stack:
            return "Artists"
        return self._stack[-1]["label"]

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

        # Breadcrumb
        if self._stack:
            label = self._current_label()
            ltex, lw, lh = assets.render_text(label, secondary)
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

            level = len(self._stack)
            if level == 0:
                display = items[i]["name"]
            elif level == 1:
                display = items[i]["name"]
                count = len(items[i]["songs"])
                display = f"{display} ({count})"
            else:
                song_idx = items[i]
                sname = STUB_SONGS[song_idx] if song_idx < len(STUB_SONGS) else f"Track {song_idx + 1}"
                num = sname.split(" - ", 1)[0] if " - " in sname else str(song_idx + 1)
                label = sname.split(" - ", 1)[1] if " - " in sname else sname
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
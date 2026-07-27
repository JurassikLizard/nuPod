"""File browser screen — stub folder/file navigation.

Shows a mock filesystem with folders and files, demonstrating
a hierarchical browse experience.
"""

from . import Screen, ScrollEvent, ButtonPress, Button
from hardware import audio
import sdl2


# Stub filesystem for the demo
STUB_FILESYSTEM = {
    "/": [
        ("folder", "Music"),
        ("folder", "Podcasts"),
        ("folder", "Playlists"),
        ("folder", "Audiobooks"),
        ("file", "readme.txt"),
        ("file", "settings.cfg"),
    ],
    "/Music": [
        ("folder", "Rock"),
        ("folder", "Pop"),
        ("folder", "Classical"),
        ("folder", "Jazz"),
        ("file", "01 - Song.mp3"),
        ("file", "02 - Track.mp3"),
        ("file", "03 - Music.mp3"),
    ],
    "/Music/Rock": [
        ("file", "Summer Days.mp3"),
        ("file", "Midnight Rain.mp3"),
        ("file", "Electric Dreams.mp3"),
        ("file", "Wanderlust.mp3"),
    ],
    "/Music/Pop": [
        ("file", "Crystal Clear.mp3"),
        ("file", "Twilight.mp3"),
        ("file", "Ocean Waves.mp3"),
    ],
    "/Music/Classical": [
        ("file", "Symphony No.1.mp3"),
        ("file", "Concerto.mp3"),
        ("file", "Sonata.mp3"),
    ],
    "/Music/Jazz": [
        ("file", "Blue Note.mp3"),
        ("file", "Autumn Leaves.mp3"),
    ],
    "/Podcasts": [
        ("file", "Episode 01.mp3"),
        ("file", "Episode 02.mp3"),
        ("file", "Episode 03.mp3"),
    ],
    "/Playlists": [
        ("file", "Favorites.m3u"),
        ("file", "Road Trip.m3u"),
        ("file", "Workout.m3u"),
    ],
    "/Audiobooks": [
        ("file", "Chapter 01.mp3"),
        ("file", "Chapter 02.mp3"),
    ],
}


class BrowseScreen(Screen):
    """Browse filesystem: folders and files."""

    def __init__(self):
        self._current_path = "/"
        self._entries = []
        self._selected = 0
        self._scroll_offset = 0
        self._refresh_entries()

    def _refresh_entries(self):
        self._entries = STUB_FILESYSTEM.get(self._current_path, [("info", "Empty folder")])
        self._selected = min(self._selected, max(0, len(self._entries) - 1))
        self._scroll_offset = 0

    def handle_input(self, event):
        if isinstance(event, ScrollEvent):
            if event.direction < 0:  # CCW = up
                self._selected = max(0, self._selected - 1)
            else:  # CW = down
                self._selected = min(len(self._entries) - 1, self._selected + 1)
            return True
        if isinstance(event, ButtonPress):
            if event.button == Button.UP:
                if self._current_path != "/":
                    parent = "/".join(self._current_path.rstrip("/").split("/")[:-1]) or "/"
                    self._current_path = parent
                    self._refresh_entries()
                    return True
                return "back"
            if event.button == Button.CENTER:
                kind, name = self._entries[self._selected]
                if kind == "folder":
                    self._current_path = f"{self._current_path.rstrip('/')}/{name}"
                    self._refresh_entries()
                elif kind == "file":
                    audio.set_title(name.rsplit(".", 1)[0])
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

        # Path breadcrumb
        text_color = self._hex_rgb(theme.get("colors", {}).get("foreground", "000000"))
        secondary = self._hex_rgb(theme.get("colors", {}).get("secondary_text", "999999"))
        sel_color = self._hex_rgb(theme.get("colors", {}).get("selector_text", "FFFFFF"))
        sel_start = self._hex_rgb(theme.get("colors", {}).get("selector_start", "5C9AE7"))
        sel_end = self._hex_rgb(theme.get("colors", {}).get("selector_end", "3268D2"))

        # Path bar
        path_display = self._current_path if len(self._current_path) < 25 else ".../" + self._current_path[-22:]
        ptex, pw, ph = assets.render_text(path_display, secondary)
        if ptex:
            dst = sdl2.SDL_Rect(vx + 4, vy + 2, pw, ph)
            sdl2.SDL_RenderCopy(renderer, ptex, None, dst)
            sdl2.SDL_DestroyTexture(ptex)

        row_h = 18
        list_y = vy + 14
        list_h = vh - 14
        visible_rows = max(1, list_h // row_h)

        if self._selected < self._scroll_offset:
            self._scroll_offset = self._selected
        elif self._selected >= self._scroll_offset + visible_rows:
            self._scroll_offset = self._selected - visible_rows + 1

        y = list_y
        end = min(len(self._entries), self._scroll_offset + visible_rows)
        for i in range(self._scroll_offset, end):
            selected = i == self._selected
            if selected:
                self._draw_gradient_bar(renderer, vx, y, vw, row_h, sel_start, sel_end)
            color = sel_color if selected else text_color

            kind, name = self._entries[i]
            prefix = ">" if kind == "folder" else " "
            display = f"{prefix} {name}"

            tex, tw, th = assets.render_text(display, color)
            if tex:
                dst = sdl2.SDL_Rect(vx + 4, y + (row_h - th) // 2, tw, th)
                sdl2.SDL_RenderCopy(renderer, tex, None, dst)
                sdl2.SDL_DestroyTexture(tex)

            y += row_h

    @staticmethod
    def _draw_gradient_bar(renderer, x, y, w, h, sel_start, sel_end, bands=8):
        for b in range(bands):
            t = b / max(1, bands - 1)
            r = int(sel_start[0] + (sel_end[0] - sel_start[0]) * t)
            g = int(sel_start[1] + (sel_end[1] - sel_start[1]) * t)
            bl = int(sel_start[2] + (sel_end[2] - sel_start[2]) * t)
            band_h = max(1, h // bands)
            sdl2.SDL_SetRenderDrawColor(renderer, r, g, bl, 255)
            sdl2.SDL_RenderFillRect(renderer, sdl2.SDL_Rect(x, y + b * band_h, w, band_h + 1))

    @staticmethod
    def _hex_rgb(h):
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
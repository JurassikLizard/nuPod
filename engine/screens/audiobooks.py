"""
Audiobooks screen — list of audiobooks with chapter navigation.

Selecting an audiobook shows its chapters, selecting a chapter starts playback.
"""

from . import Screen, ScrollEvent, ButtonPress, Button
import sdl2


STUB_AUDIOBOOKS = [
    {"title": "The Great Adventure",    "author": "Jane Explorer",  "chapters": ["Ch 1: Departure", "Ch 2: The Journey", "Ch 3: Discovery", "Ch 4: Return"]},
    {"title": "Mystery of the Cosmos",  "author": "Carl Starfield","chapters": ["Ch 1: The Question", "Ch 2: Starlight", "Ch 3: Dark Matter", "Ch 4: Answers"]},
    {"title": "Tales from the Shore",   "author": "Marina Waves",  "chapters": ["Ch 1: The Lighthouse", "Ch 2: Shipwreck", "Ch 3: Rescue"]},
    {"title": "The History of Code",    "author": "Ada Programmer","chapters": ["Ch 1: Early Days", "Ch 2: The Algorithm", "Ch 3: Modern Era", "Ch 4: Future"]},
    {"title": "Whispers in the Wind",   "author": "Zephyr Breeze", "chapters": ["Ch 1: The Letter", "Ch 2: Secrets", "Ch 3: Revelations", "Ch 4: Resolution"]},
    {"title": "Beyond the Horizon",     "author": "Sam Voyager",   "chapters": ["Ch 1: Setting Sail", "Ch 2: Open Waters", "Ch 3: New Lands"]},
]


class AudiobooksScreen(Screen):
    """Music > Audiobooks / Browse > Audiobooks: audiobook list with chapters."""

    def __init__(self):
        self._stack = []
        self._selected = 0
        self._scroll_offset = 0

    def handle_input(self, event, state):
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
                    book = STUB_AUDIOBOOKS[self._selected]
                    self._stack.append({"label": book["title"], "items": book["chapters"]})
                    self._selected = 0
                    self._scroll_offset = 0
                else:
                    chapter = self._current_items()[self._selected]
                    book_title = self._stack[0]["label"]
                    state.title = f"{book_title} - {chapter}"
                    state.artist = "Unknown"
                    state.album = book_title
                    state.elapsed_sec = 0.0
                    state.play_state = "PLAYING"
            return True
        return False

    def _current_items(self):
        if not self._stack:
            return STUB_AUDIOBOOKS
        return self._stack[-1]["items"]

    def render(self, renderer, assets, state, theme, viewport):
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
                display = items[i]["title"]
            else:
                display = items[i]

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
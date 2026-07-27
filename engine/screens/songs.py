"""Song list browser — scrollable list of stub songs.

A representative example of a list screen that isn't a menu.
Shows a scrollable list of songs with scroll position indicator.
"""

from . import Screen, ScrollEvent, ButtonPress, Button
import sdl2


# Stub song data for the demo
STUB_SONGS = [
    "01 - Intro",
    "02 - Summer Days",
    "03 - Midnight Rain",
    "04 - Electric Dreams",
    "05 - Wanderlust",
    "06 - Crystal Clear",
    "07 - Twilight",
    "08 - Ocean Waves",
    "09 - Starlight",
    "10 - Morning Sun",
    "11 - Desert Road",
    "12 - Neon Nights",
    "13 - Forgotten Path",
    "14 - Rising Tide",
    "15 - Silver Lining",
    "16 - Golden Hour",
    "17 - Deep Blue",
    "18 - Autumn Leaves",
    "19 - Winter Wind",
    "20 - New Beginnings",
    "21 - End Credits",
]


class SongsScreen(Screen):
    """Music > Songs: scrollable list of songs."""

    def __init__(self):
        self._songs = STUB_SONGS[:]
        self._selected = 0
        self._scroll_offset = 0

    def handle_input(self, event, state):
        if isinstance(event, ScrollEvent):
            if event.direction < 0:  # CCW = up
                self._selected = max(0, self._selected - 1)
            else:  # CW = down
                self._selected = min(len(self._songs) - 1, self._selected + 1)
            return True
        if isinstance(event, ButtonPress):
            if event.button == Button.UP:
                return "back"
            if event.button == Button.CENTER:
                # Play the selected song (stub)
                state.title = self._songs[self._selected].lstrip("0123456789- ").strip()
                state.artist = "Unknown Artist"
                state.album = "Unknown Album"
                state.elapsed_sec = 0.0
                state.play_state = "PLAYING"
            return True
        return False

    def render(self, renderer, assets, state, theme, viewport):
        vx, vy, vw, vh = viewport

        # Background
        bg = self._hex_rgb(theme.get("colors", {}).get("background", "FFFFFF"))
        sdl2.SDL_SetRenderDrawColor(renderer, *bg, 255)
        sdl2.SDL_RenderFillRect(renderer, sdl2.SDL_Rect(vx, vy, vw, vh))

        row_h = 18
        text_color = self._hex_rgb(theme.get("colors", {}).get("foreground", "000000"))
        sel_color = self._hex_rgb(theme.get("colors", {}).get("selector_text", "FFFFFF"))
        sel_start = self._hex_rgb(theme.get("colors", {}).get("selector_start", "5C9AE7"))
        sel_end = self._hex_rgb(theme.get("colors", {}).get("selector_end", "3268D2"))

        visible_rows = max(1, vh // row_h)

        # Update scroll
        if self._selected < self._scroll_offset:
            self._scroll_offset = self._selected
        elif self._selected >= self._scroll_offset + visible_rows:
            self._scroll_offset = self._selected - visible_rows + 1

        y = vy
        end = min(len(self._songs), self._scroll_offset + visible_rows)
        for i in range(self._scroll_offset, end):
            selected = i == self._selected
            if selected:
                self._draw_gradient_bar(renderer, vx, y, vw, row_h, sel_start, sel_end)
            color = sel_color if selected else text_color

            # Song number
            num_text = f"{i + 1}. "
            tex, nw, th = assets.render_text(num_text, color)
            if tex:
                dst = sdl2.SDL_Rect(vx + 4, y + (row_h - th) // 2, nw, th)
                sdl2.SDL_RenderCopy(renderer, tex, None, dst)
                sdl2.SDL_DestroyTexture(tex)

            # Song name
            name = self._songs[i].split(" - ", 1)[1] if " - " in self._songs[i] else self._songs[i]
            ntex, nw, th = assets.render_text(name, color)
            if ntex:
                dx = vx + 4 + nw + 4
                dst = sdl2.SDL_Rect(dx, y + (row_h - th) // 2, nw, th)
                sdl2.SDL_RenderCopy(renderer, ntex, None, dst)
                sdl2.SDL_DestroyTexture(ntex)

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
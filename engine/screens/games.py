"""
Extras/Games screen — classic iPod games.

The original iPod classic shipped with Brick, Solitaire, and other games.
This screen provides a game selection menu with stub implementations.
"""

from . import Screen, ScrollEvent, ButtonPress, Button
import sdl2


STUB_GAMES = [
    {"name": "Brick",       "desc": "Classic breakout game"},
    {"name": "Solitaire",   "desc": "Card solitaire"},
    {"name": "Music Quiz",  "desc": "Guess the song"},
    {"name": "Parachute",   "desc": "Catch the parachutists"},
]


class GamesScreen(Screen):
    """Extras > Games: game selection menu."""

    def __init__(self):
        self._selected = 0
        self._scroll_offset = 0
        self._playing = None  # name of active game

    def handle_input(self, event):
        if isinstance(event, ScrollEvent):
            if not self._playing:
                if event.direction < 0:
                    self._selected = max(0, self._selected - 1)
                else:
                    self._selected = min(len(STUB_GAMES) - 1, self._selected + 1)
            return True
        if isinstance(event, ButtonPress):
            btn = event.button
            if self._playing:
                if btn == Button.UP:
                    self._playing = None
                return True
            if btn == Button.UP:
                return "back"
            if btn == Button.CENTER:
                self._playing = STUB_GAMES[self._selected]["name"]
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

        if self._playing:
            self._render_game(renderer, assets, vx, vy, vw, vh, text_color, secondary)
            return

        row_h = 18
        visible = max(1, vh // row_h)

        if self._selected < self._scroll_offset:
            self._scroll_offset = self._selected
        elif self._selected >= self._scroll_offset + visible:
            self._scroll_offset = self._selected - visible + 1

        y = vy
        end = min(len(STUB_GAMES), self._scroll_offset + visible)
        for i in range(self._scroll_offset, end):
            sel = i == self._selected
            if sel:
                self._draw_gradient(renderer, vx, y, vw, row_h, sel_start, sel_end)
            color = sel_color if sel else text_color

            # Game name
            gtex, gw, gh = assets.render_text(STUB_GAMES[i]["name"], color)
            if gtex:
                dst = sdl2.SDL_Rect(vx + 4, y + (row_h - gh) // 2, gw, gh)
                sdl2.SDL_RenderCopy(renderer, gtex, None, dst)
                sdl2.SDL_DestroyTexture(gtex)

            # Description on right
            dtex, dw, dh = assets.render_text(STUB_GAMES[i]["desc"], secondary if not sel else sel_color)
            if dtex:
                dst = sdl2.SDL_Rect(vx + vw - dw - 4, y + (row_h - dh) // 2, dw, dh)
                sdl2.SDL_RenderCopy(renderer, dtex, None, dst)
                sdl2.SDL_DestroyTexture(dtex)

            y += row_h

    def _render_game(self, renderer, assets, vx, vy, vw, vh, text_color, secondary):
        game = self._playing

        # Game title
        gtex, gw, gh = assets.render_text(f"Now Playing: {game}", text_color)
        if gtex:
            cx = vx + (vw - gw) // 2
            dst = sdl2.SDL_Rect(cx, vy + 30, gw, gh)
            sdl2.SDL_RenderCopy(renderer, gtex, None, dst)
            sdl2.SDL_DestroyTexture(gtex)

        # Stub message
        mtex, mw, mh = assets.render_text("Game not yet implemented", secondary)
        if mtex:
            cx = vx + (vw - mw) // 2
            dst = sdl2.SDL_Rect(cx, vy + 60, mw, mh)
            sdl2.SDL_RenderCopy(renderer, mtex, None, dst)
            sdl2.SDL_DestroyTexture(mtex)

        htex, hw, hh = assets.render_text("Press BACK to return", secondary)
        if htex:
            cx = vx + (vw - hw) // 2
            dst = sdl2.SDL_Rect(cx, vy + vh - 30, hw, hh)
            sdl2.SDL_RenderCopy(renderer, htex, None, dst)
            sdl2.SDL_DestroyTexture(htex)

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
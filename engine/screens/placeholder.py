"""Placeholder screen — "Not Implemented" stub.

Used for menu items that are part of the tree but don't have
a full implementation yet. Shows a simple message.
"""

from . import Screen, ButtonPress, Button
import sdl2


class PlaceholderScreen(Screen):
    """Generic "Not Implemented" stub screen."""

    def __init__(self, title="Not Implemented", message="This feature is not yet available."):
        self._title = title
        self._message = message

    def handle_input(self, event, state):
        if isinstance(event, ButtonPress) and event.button == Button.UP:
            return "back"
        return False

    def render(self, renderer, assets, state, theme, viewport):
        vx, vy, vw, vh = viewport

        bg = self._hex_rgb(theme.get("colors", {}).get("background", "FFFFFF"))
        sdl2.SDL_SetRenderDrawColor(renderer, *bg, 255)
        sdl2.SDL_RenderFillRect(renderer, sdl2.SDL_Rect(vx, vy, vw, vh))

        text_color = self._hex_rgb(theme.get("colors", {}).get("foreground", "000000"))
        secondary = self._hex_rgb(theme.get("colors", {}).get("secondary_text", "999999"))
        title_color = self._hex_rgb(theme.get("colors", {}).get("selector_start", "5C9AE7"))

        # Title
        ttex, tw, th = assets.render_text(self._title, title_color)
        if ttex:
            cx = vx + (vw - tw) // 2
            cy = vy + vh // 2 - 20
            dst = sdl2.SDL_Rect(cx, cy, tw, th)
            sdl2.SDL_RenderCopy(renderer, ttex, None, dst)
            sdl2.SDL_DestroyTexture(ttex)

        # Message
        mtex, mw, mh = assets.render_text(self._message, secondary)
        if mtex:
            cx = vx + (vw - mw) // 2
            cy = vy + vh // 2 + 4
            dst = sdl2.SDL_Rect(cx, cy, mw, mh)
            sdl2.SDL_RenderCopy(renderer, mtex, None, dst)
            sdl2.SDL_DestroyTexture(mtex)

    @staticmethod
    def _hex_rgb(h):
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
"""Clock screen — large time display with date.

Shows the current time in a large font with the date below,
matching the iPod classic Extras > Clock screen.
"""

from . import Screen, ButtonPress, Button
import sdl2
import sdl2.sdlttf as sdlttf
import os


class ClockScreen(Screen):
    """Extras > Clock: large digital clock with date."""

    def __init__(self):
        self._large_font = None

    def _get_large_font(self, assets):
        """Get or create a larger font instance for the clock display."""
        if self._large_font is not None:
            return self._large_font
        try:
            # Try to load the large font from theme config
            theme_dir = getattr(assets, 'root', None)
            if theme_dir:
                base = os.path.dirname(theme_dir)
            else:
                base = os.path.join(os.path.dirname(__file__), '..', '..', 'theme')
            font_path = os.path.join(base, 'assets', 'font', 'Chicago.ttf')
            if os.path.exists(font_path):
                self._large_font = sdlttf.TTF_OpenFont(font_path.encode(), 24 * getattr(assets, 'scale', 1))
        except Exception:
            pass
        return self._large_font

    def handle_input(self, event, state):
        if isinstance(event, ButtonPress) and event.button == Button.UP:
            return "back"
        return False

    def render(self, renderer, assets, state, theme, viewport):
        vx, vy, vw, vh = viewport

        # Background
        bg = self._hex_rgb(theme.get("colors", {}).get("background", "FFFFFF"))
        sdl2.SDL_SetRenderDrawColor(renderer, *bg, 255)
        sdl2.SDL_RenderFillRect(renderer, sdl2.SDL_Rect(vx, vy, vw, vh))

        text_color = self._hex_rgb(theme.get("colors", {}).get("foreground", "000000"))
        secondary = self._hex_rgb(theme.get("colors", {}).get("secondary_text", "999999"))

        # Time string
        if state.clock_24h:
            time_str = f"{int(state.hour):02d}:{int(state.minute):02d}"
        else:
            h = int(state.hour) % 12 or 12
            ampm = "AM" if state.hour < 12 else "PM"
            time_str = f"{h}:{int(state.minute):02d} {ampm}"

        # Date string
        months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        month_name = months[state.month] if 1 <= state.month <= 12 else "???"
        date_str = f"{month_name} {state.day}, {state.year}"

        # Render time with large font if available
        large_font = self._get_large_font(assets)
        if large_font:
            sdl_color = sdl2.SDL_Color(text_color[0], text_color[1], text_color[2], 255)
            surf = sdlttf.TTF_RenderUTF8_Blended(large_font, time_str.encode("utf-8"), sdl_color)
            if surf:
                w, h = surf.contents.w, surf.contents.h
                tex = sdl2.SDL_CreateTextureFromSurface(renderer, surf)
                sdl2.SDL_FreeSurface(surf)
                if tex:
                    scale = getattr(assets, 'scale', 1)
                    lw, lh = w // scale, h // scale
                    cx = vx + (vw - lw) // 2
                    cy = vy + (vh - lh) // 2 - 20
                    dst = sdl2.SDL_Rect(cx, cy, lw, lh)
                    sdl2.SDL_RenderCopy(renderer, tex, None, dst)
                    sdl2.SDL_DestroyTexture(tex)
        else:
            # Fallback to regular font
            tex, tw, th = assets.render_text(time_str, text_color)
            if tex:
                cx = vx + (vw - tw) // 2
                cy = vy + (vh - th) // 2 - 20
                dst = sdl2.SDL_Rect(cx, cy, tw, th)
                sdl2.SDL_RenderCopy(renderer, tex, None, dst)
                sdl2.SDL_DestroyTexture(tex)

        # Date below time
        dtex, dw, dh = assets.render_text(date_str, secondary)
        if dtex:
            cx = vx + (vw - dw) // 2
            cy = vy + (vh - dh) // 2 + 30
            dst = sdl2.SDL_Rect(cx, cy, dw, dh)
            sdl2.SDL_RenderCopy(renderer, dtex, None, dst)
            sdl2.SDL_DestroyTexture(dtex)

    @staticmethod
    def _hex_rgb(h):
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
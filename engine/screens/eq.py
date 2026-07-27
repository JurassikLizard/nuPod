"""
Settings/EQ screen — graphical equalizer.

Shows a multi-band equalizer with adjustable frequency levels.
LEFT/RIGHT selects band, UP/DOWN adjusts level.
"""

from . import Screen, ScrollEvent, ButtonPress, Button
import sdl2


# Standard iPod classic EQ bands (Hz)
BAND_LABELS = ["50", "100", "200", "400", "1K", "2K", "4K", "8K", "16K"]
BAND_FREQS = [50, 100, 200, 400, 1000, 2000, 4000, 8000, 16000]
NUM_BANDS = len(BAND_LABELS)


class EQScreen(Screen):
    """Settings > EQ: graphic equalizer with 9 bands."""

    def __init__(self):
        self._bands = [0.0] * NUM_BANDS  # -12..+12 dB
        self._selected = 4  # start at 1KHz
        self._preset_idx = 0
        self._presets = [
            ("Flat",      [0, 0, 0, 0, 0, 0, 0, 0, 0]),
            ("Rock",      [4, 2, 0, -1, -2, -1, 0, 2, 4]),
            ("Pop",       [-1, 0, 2, 4, 4, 2, 0, -1, -2]),
            ("Jazz",      [3, 2, 1, 0, 0, 1, 2, 3, 3]),
            ("Classical", [4, 3, 1, 0, -1, -1, 0, 2, 4]),
            ("Bass Boost",[6, 5, 3, 1, 0, -1, -2, -1, 0]),
            ("Treble Boost",[-2, -1, 0, 0, 1, 2, 3, 5, 6]),
            ("Vocal",     [-1, -1, 0, 2, 4, 4, 2, 0, -1]),
            ("Dance",     [5, 4, 2, 0, -1, -1, 0, 2, 4]),
            ("Acoustic",  [4, 3, 1, 0, -1, 0, 1, 3, 4]),
        ]

    def handle_input(self, event):
        if isinstance(event, ScrollEvent):
            # Scroll wheel adjusts the selected band level
            # CCW (-1) = decrease, CW (+1) = increase
            self._bands[self._selected] = max(-12.0, min(12.0,
                self._bands[self._selected] + (1.0 if event.direction > 0 else -1.0)))
            return True
        if isinstance(event, ButtonPress):
            btn = event.button
            if btn == Button.UP:
                return "back"
            # LEFT/RIGHT select band
            if btn == Button.LEFT:
                self._selected = max(0, self._selected - 1)
            elif btn == Button.RIGHT:
                self._selected = min(NUM_BANDS - 1, self._selected + 1)
            # UP/DOWN adjust band level
            elif btn == Button.UP:
                self._bands[self._selected] = min(12.0, self._bands[self._selected] + 1.0)
            elif btn == Button.DOWN:
                self._bands[self._selected] = max(-12.0, self._bands[self._selected] - 1.0)
            # CENTER cycles presets
            elif btn == Button.CENTER:
                self._preset_idx = (self._preset_idx + 1) % len(self._presets)
                self._bands = list(self._presets[self._preset_idx][1])
            return True
        return False

    def render(self, renderer, assets, theme, viewport):
        vx, vy, vw, vh = viewport
        bg = self._hex_rgb(theme.get("colors", {}).get("background", "FFFFFF"))
        sdl2.SDL_SetRenderDrawColor(renderer, *bg, 255)
        sdl2.SDL_RenderFillRect(renderer, sdl2.SDL_Rect(vx, vy, vw, vh))

        text_color = self._hex_rgb(theme.get("colors", {}).get("foreground", "000000"))
        secondary = self._hex_rgb(theme.get("colors", {}).get("secondary_text", "999999"))
        sel_start = self._hex_rgb(theme.get("colors", {}).get("selector_start", "5C9AE7"))

        # Title
        preset_name = self._presets[self._preset_idx][0]
        title = f"EQ: {preset_name}"
        ttex, tw, th = assets.render_text(title, text_color)
        if ttex:
            cx = vx + (vw - tw) // 2
            dst = sdl2.SDL_Rect(cx, vy + 2, tw, th)
            sdl2.SDL_RenderCopy(renderer, ttex, None, dst)
            sdl2.SDL_DestroyTexture(ttex)

        # Bar graph area
        graph_y = vy + 24
        graph_h = vh - 48
        graph_mid = graph_y + graph_h // 2  # 0 dB line
        bar_w = max(6, vw // NUM_BANDS - 4)
        bar_spacing = vw // NUM_BANDS

        # Center line
        sdl2.SDL_SetRenderDrawColor(renderer, 200, 200, 200, 255)
        sdl2.SDL_RenderDrawLine(renderer, vx, graph_mid, vx + vw, graph_mid)

        # Draw bars
        for i in range(NUM_BANDS):
            level = self._bands[i]
            bar_h = int((level / 12.0) * (graph_h // 2))
            bx = vx + i * bar_spacing + (bar_spacing - bar_w) // 2

            if bar_h >= 0:
                by = graph_mid - bar_h
                bh = bar_h
            else:
                by = graph_mid
                bh = -bar_h

            if i == self._selected:
                sdl2.SDL_SetRenderDrawColor(renderer, *sel_start, 200)
            else:
                sdl2.SDL_SetRenderDrawColor(renderer, 100, 100, 100, 180)
            sdl2.SDL_RenderFillRect(renderer, sdl2.SDL_Rect(bx, by, bar_w, max(1, bh)))

            # Band label
            ltex, lw, lh = assets.render_text(BAND_LABELS[i], secondary if i != self._selected else sel_start)
            if ltex:
                lx = vx + i * bar_spacing + (bar_spacing - lw) // 2
                dst = sdl2.SDL_Rect(lx, vy + vh - 18, lw, lh)
                sdl2.SDL_RenderCopy(renderer, ltex, None, dst)
                sdl2.SDL_DestroyTexture(ltex)

        # Value display
        val = self._bands[self._selected]
        val_str = f"{val:+.0f} dB" if val != 0 else " 0 dB"
        vtex, vw_t, vh_t = assets.render_text(val_str, text_color)
        if vtex:
            cx = vx + (vw - vw_t) // 2
            dst = sdl2.SDL_Rect(cx, vy + vh - 34, vw_t, vh_t)
            sdl2.SDL_RenderCopy(renderer, vtex, None, dst)
            sdl2.SDL_DestroyTexture(vtex)

    @staticmethod
    def _hex_rgb(h):
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
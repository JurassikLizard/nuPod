"""About screen — device info display.

Shows model name, firmware version, serial number, storage capacity,
and song count in a simple info layout.
"""

from . import Screen, ButtonPress, Button
from hardware import storage
import sdl2


class AboutScreen(Screen):
    """Settings > About: device information."""

    @property
    def title(self):
        return "About"

    def handle_input(self, event):
        if isinstance(event, ButtonPress) and event.button == Button.UP:
            return "back"
        return False

    def render(self, renderer, assets, theme, viewport, dt=0.0):
        vx, vy, vw, vh = viewport

        # Background
        bg = self._hex_rgb(theme.get("colors", {}).get("background", "FFFFFF"))
        sdl2.SDL_SetRenderDrawColor(renderer, *bg, 255)
        sdl2.SDL_RenderFillRect(renderer, sdl2.SDL_Rect(vx, vy, vw, vh))

        text_color = self._hex_rgb(theme.get("colors", {}).get("foreground", "000000"))
        secondary = self._hex_rgb(theme.get("colors", {}).get("secondary_text", "999999"))
        title_color = self._hex_rgb(theme.get("colors", {}).get("selector_start", "5C9AE7"))

        lines = [
            ("About", title_color, True),
            ("", None, False),
            (f"Model: {storage.get_model_name()}", text_color, False),
            (f"Firmware: {storage.get_firmware_version()}", text_color, False),
            (f"Serial: {storage.get_serial_number()}", text_color, False),
            ("", None, False),
            (f"Capacity: {storage.get_capacity_gb()} GB", text_color, False),
            (f"Free: {storage.get_free_gb()} GB", secondary, False),
            (f"Songs: {storage.get_song_count()}", text_color, False),
            ("", None, False),
            ("Press BACK to return", secondary, False),
        ]

        y = vy + 8
        for text, color, bold in lines:
            if not text:
                y += 8
                continue
            tex, tw, th = assets.render_text(text, color)
            if tex:
                center_x = vx + (vw - tw) // 2
                dst = sdl2.SDL_Rect(center_x, y, tw, th)
                sdl2.SDL_RenderCopy(renderer, tex, None, dst)
                sdl2.SDL_DestroyTexture(tex)
                y += th + 4

    @staticmethod
    def _hex_rgb(h):
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
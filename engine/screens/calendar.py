"""
Extras/Calendar screen — monthly calendar view.

Shows a grid of days for the current month, with the current day highlighted.
LEFT/RIGHT navigate months, UP/DOWN scroll through the month grid.
"""

from . import Screen, ButtonPress, Button
import sdl2
import calendar


MONTHS = ["", "January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]


class CalendarScreen(Screen):
    """Extras > Calendar: month grid view."""

    @property
    def title(self):
        return "Calendar"

    def __init__(self):
        self._year = 2026
        self._month = 7
        self._selected = 0
        self._day_offset = 0

    def handle_input(self, event):
        if isinstance(event, ButtonPress):
            btn = event.button
            if btn == Button.UP:
                return "back"
            if btn == Button.DOWN:
                # Play/Pause not used here
                pass
            if btn == Button.RIGHT:
                self._month += 1
                if self._month > 12:
                    self._month = 1
                    self._year += 1
                self._selected = 0
            if btn == Button.CENTER:
                # Jump to the selected day (stub)
                pass
            return True
        return False

    def _get_day(self, idx):
        _, days_in_month = calendar.monthrange(self._year, self._month)
        first_weekday = calendar.monthrange(self._year, self._month)[0]
        day = idx - first_weekday + 1
        if 1 <= day <= days_in_month:
            return day
        return None

    def render(self, renderer, assets, theme, viewport, dt=0.0):
        vx, vy, vw, vh = viewport
        bg = self._hex_rgb(theme.get("colors", {}).get("background", "FFFFFF"))
        sdl2.SDL_SetRenderDrawColor(renderer, *bg, 255)
        sdl2.SDL_RenderFillRect(renderer, sdl2.SDL_Rect(vx, vy, vw, vh))

        text_color = self._hex_rgb(theme.get("colors", {}).get("foreground", "000000"))
        secondary = self._hex_rgb(theme.get("colors", {}).get("secondary_text", "999999"))
        sel_color = self._hex_rgb(theme.get("colors", {}).get("selector_text", "FFFFFF"))
        sel_start = self._hex_rgb(theme.get("colors", {}).get("selector_start", "5C9AE7"))
        sel_end = self._hex_rgb(theme.get("colors", {}).get("selector_end", "3268D2"))

        # Header: Month Year
        header = f"{MONTHS[self._month]} {self._year}"
        htex, hw, hh = assets.render_text(header, text_color)
        if htex:
            cx = vx + (vw - hw) // 2
            dst = sdl2.SDL_Rect(cx, vy + 4, hw, hh)
            sdl2.SDL_RenderCopy(renderer, htex, None, dst)
            sdl2.SDL_DestroyTexture(htex)

        # Weekday headers
        day_names = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        cell_w = vw // 7
        cell_h = 18
        for i, d in enumerate(day_names):
            dtex, dw, dh = assets.render_text(d, secondary)
            if dtex:
                dst = sdl2.SDL_Rect(vx + i * cell_w + (cell_w - dw) // 2, vy + 20, dw, dh)
                sdl2.SDL_RenderCopy(renderer, dtex, None, dst)
                sdl2.SDL_DestroyTexture(dtex)

        # Day grid
        first_weekday = calendar.monthrange(self._year, self._month)[0]
        days_in_month = calendar.monthrange(self._year, self._month)[1]
        total_cells = first_weekday + days_in_month
        rows = (total_cells + 6) // 7

        grid_y = vy + 40
        cell_h = 20

        for idx in range(total_cells):
            day = self._get_day(idx)
            if day is None:
                continue

            col = idx % 7
            row = idx // 7
            cx = vx + col * cell_w
            cy = grid_y + row * cell_h

            sel = idx == self._selected
            if sel:
                sdl2.SDL_SetRenderDrawColor(renderer, *sel_start, 255)
                sdl2.SDL_RenderFillRect(renderer, sdl2.SDL_Rect(cx, cy, cell_w, cell_h))

            color = sel_color if sel else text_color
            dtex, dw, dh = assets.render_text(str(day), color)
            if dtex:
                dst = sdl2.SDL_Rect(cx + (cell_w - dw) // 2, cy + (cell_h - dh) // 2, dw, dh)
                sdl2.SDL_RenderCopy(renderer, dtex, None, dst)
                sdl2.SDL_DestroyTexture(dtex)

    @staticmethod
    def _hex_rgb(h):
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
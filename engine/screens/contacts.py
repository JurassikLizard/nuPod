"""
Extras/Contacts screen — phonebook-style contact list.

Shows an alphabetically sorted list of contacts with phone numbers.
Selecting a contact shows their details.
"""

from . import Screen, ScrollEvent, ButtonPress, Button
import sdl2


STUB_CONTACTS = [
    ("Alice Johnson",  "555-0101"),
    ("Bob Smith",      "555-0102"),
    ("Carol Williams", "555-0103"),
    ("David Brown",    "555-0104"),
    ("Eve Davis",      "555-0105"),
    ("Frank Miller",   "555-0106"),
    ("Grace Wilson",   "555-0107"),
    ("Henry Moore",    "555-0108"),
    ("Ivy Taylor",     "555-0109"),
    ("Jack Anderson",  "555-0110"),
    ("Karen Thomas",   "555-0111"),
    ("Leo Jackson",    "555-0112"),
    ("Mia White",      "555-0113"),
    ("Noah Harris",    "555-0114"),
    ("Olivia Martin",  "555-0115"),
    ("Paul Garcia",    "555-0116"),
    ("Quinn Robinson", "555-0117"),
    ("Rose Clark",     "555-0118"),
    ("Sam Lewis",      "555-0119"),
    ("Tina Walker",    "555-0120"),
    ("Uma Hall",       "555-0121"),
    ("Victor Young",   "555-0122"),
    ("Wendy King",     "555-0123"),
    ("Xander Wright",  "555-0124"),
    ("Yara Lopez",     "555-0125"),
    ("Zoe Hill",       "555-0126"),
]


class ContactsScreen(Screen):
    """Extras > Contacts: scrollable phonebook."""

    def __init__(self):
        self._selected = 0
        self._scroll_offset = 0
        self._detail_mode = False  # show detail view for selected contact

    def handle_input(self, event):
        if isinstance(event, ScrollEvent):
            if not self._detail_mode:
                if event.direction < 0:
                    self._selected = max(0, self._selected - 1)
                else:
                    self._selected = min(len(STUB_CONTACTS) - 1, self._selected + 1)
            return True
        if isinstance(event, ButtonPress):
            btn = event.button
            if self._detail_mode:
                if btn == Button.UP:
                    self._detail_mode = False
                return True
            if btn == Button.UP:
                return "back"
            if btn == Button.CENTER:
                self._detail_mode = True
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

        if self._detail_mode:
            self._render_detail(renderer, assets, vx, vy, vw, vh, text_color, secondary)
            return

        row_h = 18
        visible = max(1, vh // row_h)

        if self._selected < self._scroll_offset:
            self._scroll_offset = self._selected
        elif self._selected >= self._scroll_offset + visible:
            self._scroll_offset = self._selected - visible + 1

        y = vy
        end = min(len(STUB_CONTACTS), self._scroll_offset + visible)
        for i in range(self._scroll_offset, end):
            sel = i == self._selected
            if sel:
                self._draw_gradient(renderer, vx, y, vw, row_h, sel_start, sel_end)
            color = sel_color if sel else text_color

            name, phone = STUB_CONTACTS[i]
            display = f"{name}"

            tex, tw, th = assets.render_text(display, color)
            if tex:
                dst = sdl2.SDL_Rect(vx + 4, y + (row_h - th) // 2, tw, th)
                sdl2.SDL_RenderCopy(renderer, tex, None, dst)
                sdl2.SDL_DestroyTexture(tex)

            # Phone number on the right
            ptex, pw, ph = assets.render_text(phone, secondary if not sel else sel_color)
            if ptex:
                dst = sdl2.SDL_Rect(vx + vw - pw - 4, y + (row_h - ph) // 2, pw, ph)
                sdl2.SDL_RenderCopy(renderer, ptex, None, dst)
                sdl2.SDL_DestroyTexture(ptex)

            y += row_h

    def _render_detail(self, renderer, assets, vx, vy, vw, vh, text_color, secondary):
        name, phone = STUB_CONTACTS[self._selected]

        # Name at top
        ntex, nw, nh = assets.render_text(name, text_color)
        if ntex:
            cx = vx + (vw - nw) // 2
            dst = sdl2.SDL_Rect(cx, vy + 30, nw, nh)
            sdl2.SDL_RenderCopy(renderer, ntex, None, dst)
            sdl2.SDL_DestroyTexture(ntex)

        # Phone
        ptex, pw, ph = assets.render_text(phone, secondary)
        if ptex:
            cx = vx + (vw - pw) // 2
            dst = sdl2.SDL_Rect(cx, vy + 60, pw, ph)
            sdl2.SDL_RenderCopy(renderer, ptex, None, dst)
            sdl2.SDL_DestroyTexture(ptex)

        # Hint
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
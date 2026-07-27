"""
Extras/Notes screen — simple text notes list.

Shows a list of notes with titles and previews. Selecting a note
shows its full content. New notes can be created (stub).
"""

from . import Screen, ScrollEvent, ButtonPress, Button
import sdl2


STUB_NOTES = [
    {"title": "Shopping List",     "body": "Milk\nEggs\nBread\nApples\nButter\nCheese"},
    {"title": "Ideas",             "body": "App idea: music player with click wheel\nWrite that song\nLearn piano"},
    {"title": "Bookmarks",         "body": "Check out the new album\nRead about audio codecs\nLook up DSP filters"},
    {"title": "Grocery",           "body": "Produce:\n- Apples\n- Bananas\n- Lettuce\nDairy:\n- Milk\n- Yogurt"},
    {"title": "Meeting Notes",     "body": "Design review:\n- New UI layout approved\n- Need to fix scroll perf\n- Add shuffle support"},
    {"title": "Playlist Ideas",    "body": "1. Summer vibes\n2. Road trip\n3. Late night coding\n4. Morning commute"},
    {"title": "Workout Plan",      "body": "Mon: Cardio\nWed: Strength\nFri: Yoga\nSun: Rest"},
]


class NotesScreen(Screen):
    """Extras > Notes: scrollable note list with detail view."""

    def __init__(self):
        self._notes = STUB_NOTES[:]
        self._selected = 0
        self._scroll_offset = 0
        self._detail_mode = False
        self._detail_scroll = 0

    def handle_input(self, event, state):
        if isinstance(event, ScrollEvent):
            if self._detail_mode:
                if event.direction < 0:
                    self._detail_scroll = max(0, self._detail_scroll - 1)
                else:
                    self._detail_scroll = min(20, self._detail_scroll + 1)
            else:
                if event.direction < 0:
                    self._selected = max(0, self._selected - 1)
                else:
                    self._selected = min(len(self._notes) - 1, self._selected + 1)
            return True
        if isinstance(event, ButtonPress):
            btn = event.button
            if self._detail_mode:
                if btn == Button.UP:
                    self._detail_mode = False
                    self._detail_scroll = 0
                return True
            if btn == Button.UP:
                return "back"
            if btn == Button.CENTER:
                self._detail_mode = True
                self._detail_scroll = 0
            return True
        return False

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
        end = min(len(self._notes), self._scroll_offset + visible)
        for i in range(self._scroll_offset, end):
            sel = i == self._selected
            if sel:
                self._draw_gradient(renderer, vx, y, vw, row_h, sel_start, sel_end)
            color = sel_color if sel else text_color

            display = self._notes[i]["title"]
            tex, tw, th = assets.render_text(display, color)
            if tex:
                dst = sdl2.SDL_Rect(vx + 4, y + (row_h - th) // 2, tw, th)
                sdl2.SDL_RenderCopy(renderer, tex, None, dst)
                sdl2.SDL_DestroyTexture(tex)
            y += row_h

    def _render_detail(self, renderer, assets, vx, vy, vw, vh, text_color, secondary):
        note = self._notes[self._selected]
        # Title
        ttex, tw, th = assets.render_text(note["title"], text_color)
        if ttex:
            dst = sdl2.SDL_Rect(vx + 4, vy + 4, tw, th)
            sdl2.SDL_RenderCopy(renderer, ttex, None, dst)
            sdl2.SDL_DestroyTexture(ttex)

        # Body (scrollable)
        lines = note["body"].split("\n")
        line_h = 16
        y = vy + 24
        visible = max(1, vh // line_h)
        end = min(len(lines), self._detail_scroll + visible)
        for i in range(self._detail_scroll, end):
            ltex, lw, lh = assets.render_text(lines[i], secondary)
            if ltex:
                dst = sdl2.SDL_Rect(vx + 4, y, lw, lh)
                sdl2.SDL_RenderCopy(renderer, ltex, None, dst)
                sdl2.SDL_DestroyTexture(ltex)
            y += line_h

        # Scroll indicator
        if len(lines) > visible:
            pct = self._detail_scroll / max(1, len(lines) - visible)
            bar_h = 4
            bar_w = max(4, 20)
            bx = vx + vw - bar_w - 4
            by = vy + 24 + int((vh - 24 - bar_h) * pct)
            sdl2.SDL_SetRenderDrawColor(renderer, 180, 180, 180, 255)
            sdl2.SDL_RenderFillRect(renderer, sdl2.SDL_Rect(bx, by, bar_w, bar_h))

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
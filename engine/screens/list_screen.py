"""Shared base class for scrollable list screens.

Eliminates the near-identical duplicate code in songs.py, albums.py,
artists.py, playlists.py, genres.py, and composers.py.

Subclasses override:
    _get_items()       → return the current level's items
    _render_item()     → render one row at (x, y, w, h)
    _on_select()       → handle CENTER press on an item
    _on_back()         → handle UP press (pop stack or return "back")
    _breadcrumb_label()→ header text when drilled in
    _item_count()      → total items at current level
"""

from . import Screen, ScrollEvent, ButtonPress, Button
import sdl2

# ── Scrollbar constants ───────────────────────────────────────────────────────

SCROLLBAR_WIDTH = 2
SCROLLBAR_TRACK_COLOR = (220, 220, 220)
SCROLLBAR_THUMB_COLOR = (160, 160, 160)
SCROLLBAR_MIN_THUMB_HEIGHT = 8


class ListScreen(Screen):
    """Scrollable list screen with drill-down navigation, gradient selection,
    breadcrumb header, and scrollbar."""

    def __init__(self):
        self._selected = 0
        self._scroll_offset = 0
        self._stack = []  # list of dicts for drill-down state
        # Animation support for drill-down navigation
        self._animator = None
        self._renderer = None
        self._assets = None
        self._theme = None
        self._viewport = None

    def set_animator(self, animator):
        """Give the screen access to the Animator for drill-down transitions."""
        self._animator = animator

    @property
    def is_animating(self):
        return self._animator is not None and self._animator.active

    @property
    def title(self):
        """Status bar title: breadcrumb when drilling in, class name at top level."""
        if self._stack:
            return self._stack[-1]["label"]
        return type(self).__name__.replace("Screen", "")

    # ── Subclass hooks ───────────────────────────────────────────────────────

    def _get_items(self):
        """Return the list of items for the current level."""
        return []

    def _item_count(self) -> int:
        return len(self._get_items())

    def _render_item(self, renderer, assets, theme, x, y, w, h, item, selected):
        """Render a single row. Override in subclass."""
        pass

    def _on_select(self, index):
        """Handle CENTER press on item at *index*.
        Return True if consumed, or "back" to close the screen."""
        return True

    def _on_back(self):
        """Handle UP press.
        Pop the stack if non-empty, otherwise return "back"."""
        return True

    def _breadcrumb_label(self):
        """Text shown in the header row when the stack is non-empty."""
        return ""

    # ── Stack helpers ────────────────────────────────────────────────────────

    def _push_stack(self, label, items):
        """Push a new navigation level onto the stack."""
        # Capture old state before stack change for animation
        self._on_stack_push()
        self._stack.append({"label": label, "items": items})
        self._selected = 0
        self._scroll_offset = 0
        # Capture new state after stack change
        self._on_stack_push_done()

    def _pop_stack(self):
        """Pop the top navigation level."""
        if self._stack:
            # Capture old state before stack change for animation
            self._on_stack_pop()
            self._stack.pop()
            self._selected = 0
            self._scroll_offset = 0
            # Capture new state after stack change
            self._on_stack_pop_done()
            return True
        return False

    def _on_stack_push(self):
        """Hook: called before a push. Captures the old screen state."""
        if self._animator and self._renderer:
            self._animator.start_push(self._render_capture)

    def _on_stack_push_done(self):
        """Hook: called after a push. Captures the new screen state."""
        if self._animator and self._renderer:
            self._animator.capture_new(self._render_capture)

    def _on_stack_pop(self):
        """Hook: called before a pop. Captures the old screen state."""
        if self._animator and self._renderer:
            self._animator.start_pop(self._render_capture)

    def _on_stack_pop_done(self):
        """Hook: called after a pop. Captures the new screen state."""
        if self._animator and self._renderer:
            self._animator.capture_new(self._render_capture)

    def _render_capture(self):
        """Render the current screen state to whichever render target is active."""
        self.render(self._renderer, self._assets, self._theme, self._viewport)

    # ── Input handling ───────────────────────────────────────────────────────

    def handle_input(self, event):
        if isinstance(event, ScrollEvent):
            n = self._item_count()
            if n == 0:
                return True
            if event.direction < 0:  # CCW = up
                self._selected = max(0, self._selected - 1)
            else:  # CW = down
                self._selected = min(n - 1, self._selected + 1)
            return True

        if isinstance(event, ButtonPress):
            btn = event.button
            if btn == Button.UP:
                if self._stack:
                    self._pop_stack()
                    return True
                return "back"
            if btn == Button.CENTER:
                return self._on_select(self._selected)
            return True

        return False

    # ── Rendering ────────────────────────────────────────────────────────────

    def render(self, renderer, assets, theme, viewport, dt=0.0):
        # Store render context for texture captures during drill-down animation
        self._renderer = renderer
        self._assets = assets
        self._theme = theme
        self._viewport = viewport

        vx, vy, vw, vh = viewport

        # No background fill — the backdrop is rendered in main.py

        text_color = self._hex_rgb(theme.get("colors", {}).get("foreground", "000000"))
        sel_color = self._hex_rgb(theme.get("colors", {}).get("selector_text", "FFFFFF"))
        sel_start = self._hex_rgb(theme.get("colors", {}).get("selector_start", "5C9AE7"))
        sel_end = self._hex_rgb(theme.get("colors", {}).get("selector_end", "3268D2"))
        secondary = self._hex_rgb(theme.get("colors", {}).get("secondary_text", "999999"))

        # Breadcrumb header — removed; title is now shown in the status bar

        items = self._get_items()
        if not items:
            return

        row_h = 18
        list_y = vy + 2
        list_h = vh - (list_y - vy)
        visible_rows = max(1, list_h // row_h)

        # Clamp scroll offset
        if self._selected < self._scroll_offset:
            self._scroll_offset = self._selected
        elif self._selected >= self._scroll_offset + visible_rows:
            self._scroll_offset = self._selected - visible_rows + 1

        # Draw rows
        y = list_y
        end = min(len(items), self._scroll_offset + visible_rows)
        for i in range(self._scroll_offset, end):
            sel = i == self._selected
            if sel:
                self._draw_gradient_bar(renderer, vx, y, vw, row_h, sel_start, sel_end)
            self._render_item(renderer, assets, theme, vx, y, vw, row_h, items[i], sel)
            y += row_h

        # Scrollbar
        self._draw_scrollbar(renderer, vx, list_y, vw, list_h,
                             visible_rows, len(items))

    # ── Scrollbar ────────────────────────────────────────────────────────────

    def _draw_scrollbar(self, renderer, vx, vy, vw, vh,
                        visible_rows, total_items):
        """Draw a thin iPod-style scrollbar on the right edge."""
        if total_items <= visible_rows:
            return

        track_x = vx + vw - SCROLLBAR_WIDTH - 3
        track_y = vy + 2
        track_h = vh - 4

        # Track
        sdl2.SDL_SetRenderDrawColor(renderer, *SCROLLBAR_TRACK_COLOR, 255)
        sdl2.SDL_RenderFillRect(renderer, sdl2.SDL_Rect(track_x, track_y, SCROLLBAR_WIDTH, track_h))

        # Thumb — slightly shorter for a visual "rounded" look
        thumb_h = max(SCROLLBAR_MIN_THUMB_HEIGHT,
                      int(track_h * visible_rows / total_items))
        max_thumb_y = track_h - thumb_h
        ratio = self._scroll_offset / max(1, total_items - visible_rows)
        thumb_y = int(track_y + ratio * max_thumb_y)

        sdl2.SDL_SetRenderDrawColor(renderer, *SCROLLBAR_THUMB_COLOR, 255)
        sdl2.SDL_RenderFillRect(renderer, sdl2.SDL_Rect(track_x, thumb_y, SCROLLBAR_WIDTH, thumb_h))

    # ── Static helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _draw_gradient_bar(renderer, x, y, w, h, c1, c2, bands=8):
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

    @staticmethod
    def _blit_text(renderer, assets, text, x, y, color):
        """Render text and blit it at (x, y), returning (tw, th)."""
        tex, tw, th = assets.render_text(text, color)
        if tex:
            dst = sdl2.SDL_Rect(int(x), int(y), int(tw), int(th))
            sdl2.SDL_RenderCopy(renderer, tex, None, dst)
            sdl2.SDL_DestroyTexture(tex)
        return tw, th
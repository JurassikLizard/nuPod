"""iPod classic menu system.

The menu tree is code-defined in menus.py; this module provides the
data model, navigation stack, and iPod-style list renderer. Each
terminus in the menu tree points to a "screen" class (a full-screen
view like Now Playing or About) or is an inline action/toggle/enum/value.

Screens and menus are mutually exclusive views — when a screen is
active the menu is hidden, matching iPod classic behavior.
"""

from dataclasses import dataclass
from typing import Callable, List, Optional, Any, Type
import sdl2

from .input import Button, ButtonPress, ScrollEvent, InputEvent


# ── data model ─────────────────────────────────────────────────────────────

@dataclass
class MenuItem:
    """One row in a menu list.

    kind:
      "submenu"  — expands to show children
      "screen"   — opens a full-screen leaf view (screen_cls)
      "action"   — calls a callback
      "toggle"   — boolean on/off via getter/setter
      "enum"     — cycles through options via getter/setter
      "value"    — numeric adjustment via getter/setter + range
    "action" items return to root after executing.
    "toggle" / "enum" / "value" items adjust in-place via LEFT/RIGHT when
    adjustment mode is active (toggled with CENTER). The scroll wheel only
    adjusts "enum" and "value" items, not toggles — toggles change via
    CENTER (enter adjust mode) then LEFT/RIGHT.
    """
    label: str
    kind: str
    children: Optional[List["MenuItem"]] = None
    screen_cls: Optional[Type] = None          # for "screen"
    action: Optional[Callable[[], None]] = None  # for "action"
    getter: Optional[Callable[[], Any]] = None   # for "toggle", "enum", "value"
    setter: Optional[Callable[[Any], None]] = None
    options: Optional[List[Any]] = None          # for "enum"
    value_range: Optional[tuple] = None          # for "value" (min, max, step)
    formatter: Optional[Callable[[Any], str]] = None  # for "value" display

    def display_value(self):
        """Right-aligned value shown in the menu row."""
        if self.kind == "toggle":
            return "On" if self.getter() else "Off"
        if self.kind == "enum":
            return str(self.getter())
        if self.kind == "value":
            val = self.getter()
            if self.formatter:
                return self.formatter(val)
            return str(val)
        return None


_ADJUSTABLE = {"toggle", "enum", "value"}


# ── factory helpers ────────────────────────────────────────────────────────

def submenu(label, children):
    return MenuItem(label, "submenu", children=children)

def screen_item(label, screen_cls):
    return MenuItem(label, "screen", screen_cls=screen_cls)

def action(label, fn):
    return MenuItem(label, "action", action=fn)

def toggle(label, getter, setter):
    return MenuItem(label, "toggle", getter=getter, setter=setter)

def enum_setting(label, getter, setter, options):
    return MenuItem(label, "enum", getter=getter, setter=setter, options=options)

def value_setting(label, getter, setter, min_val, max_val, step=1, formatter=None):
    return MenuItem(
        label, "value",
        getter=getter, setter=setter,
        value_range=(min_val, max_val, step),
        formatter=formatter,
    )


# ── navigation stack ───────────────────────────────────────────────────────

class MenuScreen:
    """One level of the menu stack: a list of items plus scroll/selection
    state. MenuController holds a stack of these for back-navigation."""

    def __init__(self, title, items):
        self.title = title
        self.items = items
        self.selected = 0
        self.scroll_offset = 0
        self.adjust_mode = False  # True when adjusting a value in-place

    def move(self, delta):
        if self.items and not self.adjust_mode:
            self.selected = (self.selected + delta) % len(self.items)

    def current(self):
        return self.items[self.selected] if self.items else None


class MenuController:
    """Owns the navigation stack and interprets abstract InputEvent values.

    The root menu is always present — it is the top-level object that never
    goes away. BACK on the root does nothing; MENU returns to root; actions
    return to root after executing. The menu is only hidden when a full-screen
    view (ScreenManager) is active.
    """

    def __init__(self, root_items, root_title="Main Menu",
                 on_push=None, on_pop=None,
                 on_post_push=None, on_post_pop=None):
        self._root_items = root_items
        self._root_title = root_title
        self._on_push = on_push
        self._on_pop = on_pop
        self._on_post_push = on_post_push
        self._on_post_pop = on_post_pop
        self.stack = [MenuScreen(self._root_title, self._root_items)]

    @property
    def active(self):
        return True

    def go_to_root(self):
        self.stack = self.stack[:1]
        self.stack[0].selected = 0
        self.stack[0].scroll_offset = 0
        self.stack[0].adjust_mode = False

    def rebuild_root(self, items):
        """Replace the root menu's items (e.g. after Now Playing state changes)."""
        self.stack[0].items = items
        self.stack[0].selected = 0
        self.stack[0].scroll_offset = 0
        self.stack[0].adjust_mode = False

    def go_back_one(self):
        """Pop one level unless already at root. Returns True if popped."""
        if len(self.stack) > 1:
            self.stack.pop()
            return True
        return False

    def handle(self, event: InputEvent) -> None:
        """Consume one input event, updating menu state."""
        screen = self.stack[-1]
        item = screen.current()

        # ── scroll wheel ────────────────────────────────────────────────
        if isinstance(event, ScrollEvent):
            if screen.adjust_mode and item and item.kind in ("enum", "value"):
                # Scroll adjusts enum/value in adjust mode, but NOT toggles
                self._adjust_value(item, -1 if event.direction < 0 else 1)
            else:
                # Scroll navigates the list.  CCW (-1) = move up, CW (+1) = move down.
                screen.move(-1 if event.direction < 0 else 1)
            return

        if not isinstance(event, ButtonPress):
            return

        btn = event.button

        # ── UP (Menu) button: short = back one, long = root ────────────
        if btn == Button.UP:
            if event.long_press:
                self.go_to_root()
            else:
                if screen.adjust_mode:
                    screen.adjust_mode = False
                elif len(self.stack) > 1:
                    if self._on_pop:
                        self._on_pop()
                    self.stack.pop()
                    if self._on_post_pop:
                        self._on_post_pop()
            return

        # ── LEFT (Rewind / adjust left) ─────────────────────────────────
        if btn == Button.LEFT:
            if screen.adjust_mode and item and item.kind in _ADJUSTABLE:
                self._adjust_value(item, -1)
            return

        # ── RIGHT (Forward / adjust right) ──────────────────────────────
        if btn == Button.RIGHT:
            if screen.adjust_mode and item and item.kind in _ADJUSTABLE:
                self._adjust_value(item, 1)
            return

        # ── DOWN (Play/Pause) button ────────────────────────────────────
        if btn == Button.DOWN:
            if screen.adjust_mode and item and item.kind in _ADJUSTABLE:
                self._adjust_value(item, -1)
            return

        # ── CENTER (Select) button ──────────────────────────────────────
        if btn == Button.CENTER and item:
            if screen.adjust_mode:
                screen.adjust_mode = False
                return
            if item.kind in _ADJUSTABLE:
                screen.adjust_mode = True
                return
            if item.kind == "submenu":
                if self._on_push:
                    self._on_push()
                self.stack.append(MenuScreen(item.label, item.children))
                if self._on_post_push:
                    self._on_post_push()
                return
            if item.kind == "action":
                self.go_to_root()
                item.action()
                return
            # "screen" — the main loop catches this via get_selected_screen_cls()
            return

    def _adjust_value(self, item: MenuItem, direction: int) -> None:
        if item.kind == "toggle":
            item.setter(not item.getter())
        elif item.kind == "enum":
            self._cycle_enum(item, direction)
        elif item.kind == "value":
            lo, hi, step = item.value_range
            val = item.getter()
            item.setter(max(lo, min(hi, val + step * direction)))

    def _cycle_enum(self, item: MenuItem, direction: int) -> None:
        opts = item.options
        try:
            idx = opts.index(item.getter())
        except ValueError:
            idx = 0
        item.setter(opts[(idx + direction) % len(opts)])

    def get_selected_screen_cls(self):
        if not self.stack:
            return None
        item = self.stack[-1].current()
        if item and item.kind == "screen":
            return item.screen_cls
        return None


# ── rendering ───────────────────────────────────────────────────────────────

class MenuRenderer:
    """Draws the top of the MenuController's stack in iPod classic style:
    white background, blue gradient selection bar, Chicago font text,
    right-aligned values for settings, chevron for submenus."""

    def __init__(self, renderer, assets, style, viewport):
        self.renderer = renderer
        self.assets = assets
        self.row_h = style.get("row_height", 18)
        self.text_color = style["text_color"]
        self.bg_color = style["background_color"]
        self.sel_start = style["selector_start"]
        self.sel_end = style["selector_end"]
        self.sel_text_color = style["selector_text_color"]
        self.secondary_color = style.get("secondary_text_color", (120, 120, 120))
        self.vx, self.vy, self.vw, self.vh = viewport

    def render(self, controller: MenuController):
        if not controller.active:
            return
        screen = controller.stack[-1]

        sdl2.SDL_RenderSetClipRect(self.renderer, sdl2.SDL_Rect(self.vx, self.vy, self.vw, self.vh))
        sdl2.SDL_SetRenderDrawColor(self.renderer, *self.bg_color, 255)
        sdl2.SDL_RenderFillRect(self.renderer, sdl2.SDL_Rect(self.vx, self.vy, self.vw, self.vh))

        visible_rows = max(1, self.vh // self.row_h)
        self._update_scroll(screen, visible_rows)

        y = self.vy
        end = min(len(screen.items), screen.scroll_offset + visible_rows)
        for i in range(screen.scroll_offset, end):
            self._render_row(screen.items[i], i == screen.selected, y, screen.adjust_mode)
            y += self.row_h

        # Scrollbar
        self._draw_scrollbar(screen, visible_rows)

        sdl2.SDL_RenderSetClipRect(self.renderer, None)

    def _update_scroll(self, screen, visible_rows):
        if screen.selected < screen.scroll_offset:
            screen.scroll_offset = screen.selected
        elif screen.selected >= screen.scroll_offset + visible_rows:
            screen.scroll_offset = screen.selected - visible_rows + 1

    def _render_row(self, item, selected, y, adjust_mode=False):
        color = self.sel_text_color if selected else self.text_color
        value_color = self.sel_text_color if selected else self.secondary_color

        if selected:
            self._draw_gradient_bar(self.vx, y, self.vw, self.row_h)

        # Label (with adjust-mode indicator)
        label = f"* {item.label}" if selected and adjust_mode and item.kind != "toggle" else item.label
        self._blit_text(label, self.vx + 4, y, color, align="left")

        # Right-aligned value or chevron
        value = item.display_value()
        if value is not None:
            self._blit_text(value, self.vx + self.vw - 4, y, value_color, align="right")
        elif item.kind in ("submenu", "screen"):
            self._blit_text(">", self.vx + self.vw - 4, y, value_color, align="right")

    def _blit_text(self, text, x, y, color, align):
        tex, raw_tw, raw_th = self.assets.render_text(text, color)
        if not tex:
            return
        tw, th = int(raw_tw), int(raw_th)
        dx = x if align == "left" else x - tw
        dst = sdl2.SDL_Rect(int(dx), int(y + (self.row_h - th) / 2), tw, th)
        sdl2.SDL_RenderCopy(self.renderer, tex, None, dst)
        sdl2.SDL_DestroyTexture(tex)

    def _draw_gradient_bar(self, x, y, w, h, bands=8):
        for b in range(bands):
            t = b / max(1, bands - 1)
            r = int(self.sel_start[0] + (self.sel_end[0] - self.sel_start[0]) * t)
            g = int(self.sel_start[1] + (self.sel_end[1] - self.sel_start[1]) * t)
            bl = int(self.sel_start[2] + (self.sel_end[2] - self.sel_start[2]) * t)
            band_h = max(1, h // bands)
            sdl2.SDL_SetRenderDrawColor(self.renderer, r, g, bl, 255)
            sdl2.SDL_RenderFillRect(self.renderer, sdl2.SDL_Rect(x, y + b * band_h, w, band_h + 1))

    # ── Scrollbar ────────────────────────────────────────────────────────────────

    SCROLLBAR_WIDTH = 2
    SCROLLBAR_TRACK_COLOR = (220, 220, 220)
    SCROLLBAR_THUMB_COLOR = (160, 160, 160)
    SCROLLBAR_MIN_THUMB_HEIGHT = 8

    def _draw_scrollbar(self, screen, visible_rows):
        total_items = len(screen.items)
        if total_items <= visible_rows:
            return

        track_x = self.vx + self.vw - self.SCROLLBAR_WIDTH - 3
        track_y = self.vy + 2
        track_h = self.vh - 4

        # Track
        sdl2.SDL_SetRenderDrawColor(self.renderer, *self.SCROLLBAR_TRACK_COLOR, 255)
        sdl2.SDL_RenderFillRect(self.renderer, sdl2.SDL_Rect(track_x, track_y, self.SCROLLBAR_WIDTH, track_h))

        # Thumb — shorter by 2px top/bottom for visual "rounded" look
        thumb_h = max(self.SCROLLBAR_MIN_THUMB_HEIGHT,
                      int(track_h * visible_rows / total_items))
        max_thumb_y = track_h - thumb_h
        ratio = screen.scroll_offset / max(1, total_items - visible_rows)
        thumb_y = int(track_y + ratio * max_thumb_y)

        sdl2.SDL_SetRenderDrawColor(self.renderer, *self.SCROLLBAR_THUMB_COLOR, 255)
        sdl2.SDL_RenderFillRect(self.renderer, sdl2.SDL_Rect(track_x, thumb_y, self.SCROLLBAR_WIDTH, thumb_h))
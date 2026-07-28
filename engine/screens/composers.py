"""Music/Composers screen — placeholder until composer metadata is available.

Shows a single "Not yet available" message.
"""

from . import Button
from .list_screen import ListScreen


class ComposersScreen(ListScreen):
    """Music > Composers: placeholder."""

    def __init__(self):
        super().__init__()
        self._items = [{"label": "Not yet available", "id": "empty"}]

    def _get_items(self):
        return self._items

    def _item_count(self):
        return len(self._items)

    def _render_item(self, renderer, assets, theme, x, y, w, h, item, selected):
        text_color = theme.get("colors", {}).get("foreground", "000000")
        sel_color = theme.get("colors", {}).get("selector_text", "FFFFFF")
        secondary = theme.get("colors", {}).get("secondary_text", "999999")
        color = self._hex_rgb(sel_color if selected else secondary)
        self._blit_text(renderer, assets, item["label"], x + 4, y + (h - 10) // 2, color)

    def _on_select(self, index):
        return True

    def _on_back(self):
        return "back"
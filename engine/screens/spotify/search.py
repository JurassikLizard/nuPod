"""Spotify > Search — character-by-character search input.

Uses a scrollable character picker (A-Z, 0-9, space, backspace, enter)
to build a search query. Selecting "Search" executes the query and
shows results in a standard drill-down list.

Flow:
  1. Scroll through characters, CENTER to add to query
  2. Select "Search" to search, "Clear" to reset
  3. Results appear as a drill-down list (tracks drill into album)
"""

from ..list_screen import ListScreen
from .. import Button, ButtonPress, ScrollEvent
from engine.spotify_client import get_client
from . import play_spotify_track
import sdl2


# Characters available for search
CHARS = [chr(i) for i in range(ord("A"), ord("Z") + 1)]
CHARS += [str(i) for i in range(10)]
CHARS += [" ", ".", "-", "&", "'"]
CHARS += ["⌫", "⏎ Search", "✕ Clear"]

# How many characters to show at once
VISIBLE_CHARS = 8


class SpotifySearchScreen(ListScreen):
    """Spotify > Search: character-by-character input."""

    def __init__(self):
        super().__init__()
        self._query = ""
        self._char_index = 0  # scroll position in character list
        self._char_selected = 0  # which char is highlighted
        self._results = []
        self._in_results = False
        self._result_type = "track"
        self._tracks_cache = {}
        self._albums_cache = {}
        # Results drill-down: when showing album/playlist tracks, push here
        self._result_items = []

    @property
    def title(self):
        return "Search"

    def _get_items(self):
        if self._in_results:
            if self._stack:
                return self._stack[-1]["items"]
            return self._results
        return CHARS

    def _item_count(self):
        return len(self._get_items())

    def _render_item(self, renderer, assets, theme, x, y, w, h, item, selected):
        text_color = theme.get("colors", {}).get("foreground", "000000")
        sel_color = theme.get("colors", {}).get("selector_text", "FFFFFF")
        color = self._hex_rgb(sel_color if selected else text_color)
        secondary = theme.get("colors", {}).get("secondary_text", "999999")

        if self._in_results:
            # Results view
            if isinstance(item, dict):
                label = item.get("name", item.get("title", "Unknown"))
                if item.get("artist"):
                    label += f" — {item['artist']}"
                if item.get("track_number"):
                    label = f"{item['track_number']}. {label}"
            else:
                label = str(item)
            self._blit_text(renderer, assets, label, x + 4, y + (h - 10) // 2, color)
        else:
            # Character picker — center the character
            label = str(item)
            tw, th = 0, 0
            tex, tw, th = assets.render_text(label, color)
            if tex:
                cx = x + (w - tw) // 2
                dst = sdl2.SDL_Rect(cx, y + (h - th) // 2, tw, th)
                sdl2.SDL_RenderCopy(renderer, tex, None, dst)
                sdl2.SDL_DestroyTexture(tex)

    # ── Input handling ──────────────────────────────────────────────────────

    def handle_input(self, event):
        if isinstance(event, ScrollEvent):
            n = self._item_count()
            if n == 0:
                return True
            if self._in_results and not self._stack:
                # Scroll through results
                if event.direction < 0:
                    self._selected = max(0, self._selected - 1)
                else:
                    self._selected = min(n - 1, self._selected + 1)
            else:
                # Scroll through character picker
                if event.direction < 0:
                    self._char_selected = max(0, self._char_selected - 1)
                else:
                    self._char_selected = min(n - 1, self._char_selected + 1)
            return True

        if isinstance(event, ButtonPress):
            btn = event.button
            if btn == Button.UP:
                if self._stack:
                    self._pop_stack()
                    return True
                if self._in_results:
                    # Go back to search
                    self._in_results = False
                    self._results = []
                    self._result_items = []
                    return True
                return "back"

            if btn == Button.CENTER:
                if self._in_results and not self._stack:
                    # Select a result item
                    return self._on_select_result(self._selected)
                elif self._stack:
                    return self._on_select_result(self._selected)
                else:
                    return self._on_char_selected(self._char_selected)
            return True
        return False

    def _on_char_selected(self, index):
        if index < 0 or index >= len(CHARS):
            return True
        char = CHARS[index]

        if char == "⌫":
            # Backspace
            self._query = self._query[:-1]
            return True
        elif char == "⏎ Search":
            # Execute search
            self._execute_search()
            return True
        elif char == "✕ Clear":
            # Clear query
            self._query = ""
            return True
        else:
            # Add character to query
            if len(self._query) < 50:  # limit query length
                self._query += char
            return True

    def _execute_search(self):
        query = self._query.strip()
        if not query:
            return

        client = get_client()
        if not client.is_authenticated():
            return

        # Search for tracks and albums (limit max 10 per Spotify API)
        tracks = client.search(query, search_type="track", limit=10)
        albums = client.search(query, search_type="album", limit=10)
        artists = client.search(query, search_type="artist", limit=10)
        playlists = client.search(query, search_type="playlist", limit=10)

        # Build combined results
        results = []

        # Tracks section
        results.append({"type": "header", "label": "── Tracks ──"})
        if tracks:
            results.extend(tracks[:10])
        else:
            results.append({"type": "empty", "label": "(no tracks)"})

        # Albums section
        results.append({"type": "header", "label": "── Albums ──"})
        if albums:
            results.extend(albums[:5])
        else:
            results.append({"type": "empty", "label": "(no albums)"})

        # Artists section
        results.append({"type": "header", "label": "── Artists ──"})
        if artists:
            results.extend(artists[:5])
        else:
            results.append({"type": "empty", "label": "(no artists)"})

        # Playlists section
        results.append({"type": "header", "label": "── Playlists ──"})
        if playlists:
            results.extend(playlists[:5])
        else:
            results.append({"type": "empty", "label": "(no playlists)"})

        self._results = results
        self._in_results = True
        self._selected = 0

    def _on_select_result(self, index):
        items = self._get_items()
        if index < 0 or index >= len(items):
            return True

        item = items[index]
        if isinstance(item, dict):
            item_type = item.get("type", "")
            item_id = item.get("id", "")

            if item_type in ("header", "empty"):
                return True  # Not selectable

            # Check if it's a track (has 'title' or 'uri')
            if item.get("uri", "").startswith("spotify:track:"):
                self._play_track(index, items)
                return True

            # Album: show tracks
            if item.get("uri", "").startswith("spotify:album:"):
                aid = item.get("id")
                if aid and aid not in self._tracks_cache:
                    client = get_client()
                    tracks = client.get_album_tracks(aid, limit=50)
                    self._tracks_cache[aid] = tracks
                tracks = self._tracks_cache.get(aid, [])
                if tracks:
                    self._push_stack(item.get("name", "Album"), tracks)
                return True

            # Artist: show albums
            if item.get("uri", "").startswith("spotify:artist:"):
                aid = item.get("id")
                if aid and aid not in self._albums_cache:
                    client = get_client()
                    albums = client.get_artist_albums(aid, limit=50)
                    self._albums_cache[aid] = albums
                albums = self._albums_cache.get(aid, [])
                if albums:
                    self._push_stack(item.get("name", "Artist"), albums)
                return True

            # Playlist: show tracks
            if item.get("uri", "").startswith("spotify:playlist:"):
                pid = item.get("id")
                if pid and pid not in self._tracks_cache:
                    client = get_client()
                    tracks = client.get_playlist_tracks(pid, limit=100)
                    self._tracks_cache[pid] = tracks
                tracks = self._tracks_cache.get(pid, [])
                if tracks:
                    self._push_stack(item.get("name", "Playlist"), tracks)
                return True

            # Fallback: try to play as track
            if item.get("uri"):
                self._play_track(index, items)
                return True

        return True

    def _play_track(self, index, items):
        if index >= len(items):
            return

        # Collect all track URIs from the current list
        uris = [t["uri"] for t in items if isinstance(t, dict) and t.get("uri", "").startswith("spotify:track:")]

        if not uris:
            return

        play_spotify_track(uris, start_index=min(index, len(uris) - 1))

    # ── Rendering with query display ────────────────────────────────────────

    def render(self, renderer, assets, theme, viewport, dt=0.0):
        # Store render context for animations
        self._renderer = renderer
        self._assets = assets
        self._theme = theme
        self._viewport = viewport

        vx, vy, vw, vh = viewport
        text_color = self._hex_rgb(theme.get("colors", {}).get("foreground", "000000"))
        sel_color = self._hex_rgb(theme.get("colors", {}).get("selector_text", "FFFFFF"))
        sel_start = self._hex_rgb(theme.get("colors", {}).get("selector_start", "5C9AE7"))
        sel_end = self._hex_rgb(theme.get("colors", {}).get("selector_end", "3268D2"))
        secondary = self._hex_rgb(theme.get("colors", {}).get("secondary_text", "999999"))

        if self._in_results:
            # Render results list
            items = self._get_items()
            if not items:
                return

            row_h = 18
            list_y = vy + 20  # leave room for query display
            list_h = vh - 20
            visible_rows = max(1, list_h // row_h)

            # Draw query at top
            query_display = f'"{self._query}"'
            qtex, qw, qh = assets.render_text(query_display, text_color)
            if qtex:
                dst = sdl2.SDL_Rect(vx + 4, vy + 2, qw, qh)
                sdl2.SDL_RenderCopy(renderer, qtex, None, dst)
                sdl2.SDL_DestroyTexture(qtex)

            # Separator
            sdl2.SDL_SetRenderDrawColor(renderer, 180, 180, 180, 255)
            sdl2.SDL_RenderDrawLine(renderer, vx, vy + 18, vx + vw, vy + 18)

            # Cursor in results
            cursor = self._selected
            if cursor < self._scroll_offset:
                self._scroll_offset = cursor
            elif cursor >= self._scroll_offset + visible_rows:
                self._scroll_offset = cursor - visible_rows + 1

            y = list_y
            end = min(len(items), self._scroll_offset + visible_rows)
            for i in range(self._scroll_offset, end):
                sel = i == cursor
                if sel:
                    self._draw_gradient_bar(renderer, vx, y, vw, row_h, sel_start, sel_end)
                item = items[i]
                if isinstance(item, dict):
                    item_type = item.get("type", "")
                    if item_type == "header":
                        hcolor = secondary
                        htex, hw, hh = assets.render_text(item.get("label", ""), hcolor)
                        if htex:
                            dst = sdl2.SDL_Rect(vx + 4, y + (row_h - hh) // 2, hw, hh)
                            sdl2.SDL_RenderCopy(renderer, htex, None, dst)
                            sdl2.SDL_DestroyTexture(htex)
                    elif item_type == "empty":
                        etex, ew, eh = assets.render_text(item.get("label", ""), secondary)
                        if etex:
                            dst = sdl2.SDL_Rect(vx + 8, y + (row_h - eh) // 2, ew, eh)
                            sdl2.SDL_RenderCopy(renderer, etex, None, dst)
                            sdl2.SDL_DestroyTexture(etex)
                    else:
                        self._render_item(renderer, assets, theme, vx, y, vw, row_h, item, sel)
                y += row_h

            self._draw_scrollbar(renderer, vx, list_y, vw, list_h,
                                 visible_rows, len(items))
        else:
            # Render character picker with query display
            row_h = 28  # bigger rows for character picker
            list_y = vy + 24
            list_h = vh - 24
            visible_rows = max(1, list_h // row_h)

            # Draw query at top
            query_display = self._query + "█" if len(self._query) < 50 else self._query
            qtex, qw, qh = assets.render_text(query_display, text_color)
            if qtex:
                clip = sdl2.SDL_Rect(vx, vy, vw - 4, 22)
                sdl2.SDL_RenderSetClipRect(renderer, clip)
                dst = sdl2.SDL_Rect(vx + 4, vy + 2, qw, qh)
                sdl2.SDL_RenderCopy(renderer, qtex, None, dst)
                sdl2.SDL_RenderSetClipRect(renderer, None)
                sdl2.SDL_DestroyTexture(qtex)

            # Separator
            sdl2.SDL_SetRenderDrawColor(renderer, 180, 180, 180, 255)
            sdl2.SDL_RenderDrawLine(renderer, vx, vy + 22, vx + vw, vy + 22)

            # Character grid
            cursor = self._char_selected
            if cursor < self._char_index:
                self._char_index = cursor
            elif cursor >= self._char_index + visible_rows:
                self._char_index = cursor - visible_rows + 1

            y = list_y
            end = min(len(CHARS), self._char_index + visible_rows)
            for i in range(self._char_index, end):
                sel = i == cursor
                if sel:
                    self._draw_gradient_bar(renderer, vx, y, vw, row_h, sel_start, sel_end)
                char = CHARS[i]
                color = sel_color if sel else text_color
                ctex, cw, ch = assets.render_text(char, color)
                if ctex:
                    cx = vx + (vw - cw) // 2
                    dst = sdl2.SDL_Rect(cx, y + (row_h - ch) // 2, cw, ch)
                    sdl2.SDL_RenderCopy(renderer, ctex, None, dst)
                    sdl2.SDL_DestroyTexture(ctex)
                y += row_h

            self._draw_scrollbar(renderer, vx, list_y, vw, list_h,
                                 visible_rows, len(CHARS))

    # ── Helpers from parent we override to avoid calling _get_items ──────────

    def _on_back(self):
        if self._stack:
            self._clear_stack()
            return True
        if self._in_results:
            self._in_results = False
            self._results = []
            self._result_items = []
            return True
        return "back"

    def _clear_stack(self):
        self._stack = []
        self._selected = 0
        self._scroll_offset = 0
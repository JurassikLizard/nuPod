"""Now Playing screen — iPod classic playback view.

Shows album art (or centered text when no art), track metadata,
progress bar, and time info.  Compact layout for the 160×128 canvas.
"""

from . import Screen, ButtonPress, Button
from hardware import audio, volume, settings as hwsettings
import sdl2


class NowPlayingScreen(Screen):
    """Full-screen Now Playing display with album art, track info, progress bar."""

    @property
    def title(self):
        return "Now Playing"

    MARQUEE_SPEED_PX_S = 20
    MARQUEE_GAP_PX = 16

    def __init__(self):
        self._scroll_offsets = {}

    # ---- content area ------------------------------------------------------

    def _render_content(self, renderer, assets, theme, viewport, dt=1/60):
        vx, vy, vw, vh = viewport  # (0, 22, 160, 106)
        cy = vy

        album_art_path = audio.get_album_art_path()

        if album_art_path:
            self._render_album_art_layout(renderer, assets, vx, cy, vw, vh, dt)
        else:
            self._render_no_art_layout(renderer, assets, vx, cy, vw, vh, dt)

        # Shuffle/repeat icons (top of content area)
        self._render_mode_indicators(renderer, assets, vx, cy + 2, vw)

        # Playlist position
        pos_text = f"{audio.get_playlist_pos()} of {audio.get_playlist_len()}"
        pos_color = self._hex_rgb(theme.get("colors", {}).get("secondary_text", "999999"))
        pos_tex, ptw, pth = assets.render_text(pos_text, pos_color)
        if pos_tex:
            dst = sdl2.SDL_Rect(vx + 4, cy + 2, ptw, pth)
            sdl2.SDL_RenderCopy(renderer, pos_tex, None, dst)
            sdl2.SDL_DestroyTexture(pos_tex)

        # Separator line above progress bar
        self._render_separator(renderer, vx, cy, vw)

        # Progress bar at bottom
        self._render_progress_bar(renderer, assets, vx, cy, vw, vh)

        # Elapsed / remaining time
        self._render_time_info(renderer, assets, vx, cy, vw, vh)

    def _render_album_art_layout(self, renderer, assets, ox, oy, cw, ch, dt=1/60):
        """Album art on the left, track info alongside."""
        ART_SIZE = 50
        try:
            tex, tw, th = assets.get_dynamic_texture(
                audio.get_album_art_path(), max_size=(ART_SIZE, ART_SIZE),
            )
        except Exception:
            tex = None
        if tex:
            art_x = ox + 5 + (ART_SIZE - tw) // 2
            art_y = oy + 18 + (ART_SIZE - th) // 2
            dst = sdl2.SDL_Rect(art_x, art_y, tw, th)
            sdl2.SDL_RenderCopy(renderer, tex, None, dst)

        # Track info, right of art
        info_x = ox + 60
        info_w = cw - 65  # ~95px
        text_color = self._hex_rgb("000000")
        items = [
            (audio.get_title() if audio.has_id3() else audio.get_filename(), 20),
            (audio.get_artist() if audio.has_id3() and audio.get_artist() else None, 40),
            (audio.get_album() if audio.has_id3() and audio.get_album() else None, 56),
        ]
        for text, y in items:
            if text is None:
                continue
            self._draw_marquee_text(renderer, assets, text, info_x, oy + y, info_w, text_color, id(text), dt=dt)

    def _render_no_art_layout(self, renderer, assets, ox, oy, cw, ch, dt=1/60):
        """Centered text when no album art."""
        text_color = self._hex_rgb("000000")
        items = [
            (audio.get_title() if audio.has_id3() else audio.get_filename(), 20),
            (audio.get_artist() if audio.has_id3() and audio.get_artist() else None, 40),
            (audio.get_album() if audio.has_id3() and audio.get_album() else None, 56),
        ]
        for text, y in items:
            if text is None:
                continue
            self._draw_marquee_text(renderer, assets, text, ox, oy + y, cw, text_color, id(text), center=True, dt=dt)

    def _draw_marquee_text(self, renderer, assets, text, x, y, w, color, key, center=False, dt=1/60):
        tex, tw, th = assets.render_text(text, color)
        if not tex:
            return
        if tw <= w:
            dx = x + (w - tw) // 2 if center else x
            dst = sdl2.SDL_Rect(int(dx), int(y), int(tw), int(th))
            sdl2.SDL_RenderCopy(renderer, tex, None, dst)
        else:
            total = tw + self.MARQUEE_GAP_PX
            offset = self._scroll_offsets.get(key, 0.0)
            offset = (offset + dt * self.MARQUEE_SPEED_PX_S) % total
            self._scroll_offsets[key] = offset
            clip = sdl2.SDL_Rect(int(x), int(y), int(w), int(th))
            sdl2.SDL_RenderSetClipRect(renderer, clip)
            for shift in (0, total):
                dst = sdl2.SDL_Rect(int(x - offset + shift), int(y), int(tw), int(th))
                sdl2.SDL_RenderCopy(renderer, tex, None, dst)
            sdl2.SDL_RenderSetClipRect(renderer, None)
        sdl2.SDL_DestroyTexture(tex)

    def _render_mode_indicators(self, renderer, assets, ox, oy, cw):
        """Shuffle and repeat icons at the top-right."""
        x = ox + cw - 4
        if hwsettings.get_repeat_mode() != "OFF":
            tex, fw, fh, frames = assets.get_sprite("repeat")
            if tex:
                frame = {"ALL": 0, "ONE": 1, "AB": 2, "SHUFFLE": 3}.get(hwsettings.get_repeat_mode(), 0)
                src = sdl2.SDL_Rect(0, frame * fh, fw, fh)
                x -= fw + 2
                dst = sdl2.SDL_Rect(x, oy, fw, fh)
                sdl2.SDL_RenderCopy(renderer, tex, src, dst)
        if hwsettings.is_shuffle_enabled():
            tex, fw, fh, _ = assets.get_sprite("shuffle")
            if tex:
                x -= fw + 2
                dst = sdl2.SDL_Rect(x, oy, fw, fh)
                sdl2.SDL_RenderCopy(renderer, tex, None, dst)

    def _render_separator(self, renderer, ox, oy, cw):
        """Thin horizontal line above the progress bar."""
        sdl2.SDL_SetRenderDrawColor(renderer, 180, 180, 180, 255)
        sdl2.SDL_RenderDrawLine(renderer, ox + 8, oy + 76, ox + cw - 8, oy + 76)

    def _render_progress_bar(self, renderer, assets, ox, oy, cw, ch):
        if volume.is_volume_mode_active():
            img_name = "volume_bar"
            value = volume.get_volume_percent() / 100.0
        else:
            img_name = "progress_bar"
            value = audio.get_track_progress()
        tex, iw, ih = assets.get_texture(img_name)
        if not tex:
            return
        # Bar fits within the canvas: x=8, width=144 (cw-16)
        x, y = ox + 8, oy + 80
        bar_w = cw - 16  # 144
        bar_h = 10

        # The backdrop already has the progress bar track background,
        # so we only render the fill on top.

        # Progress fill on top of the backdrop's built-in bar track
        fill_w = int(bar_w * value)
        if audio.is_audio_active() or volume.is_volume_mode_active():
            fill_w = max(1, fill_w)
        if fill_w > 0:
            src = sdl2.SDL_Rect(0, 0, fill_w, ih)
            dst = sdl2.SDL_Rect(x, y, fill_w, bar_h)
            sdl2.SDL_RenderCopy(renderer, tex, src, dst)

        # Volume mode left/right icons
        if volume.is_volume_mode_active():
            il, ilw, ilh = assets.get_texture("vol_left")
            if il:
                sdl2.SDL_RenderCopy(renderer, il, None, sdl2.SDL_Rect(ox + 4, oy + 77, ilw, ilh))
            ir, irw, irh = assets.get_texture("vol_right")
            if ir:
                sdl2.SDL_RenderCopy(renderer, ir, None, sdl2.SDL_Rect(ox + cw - 4 - irw, oy + 77, irw, irh))

    def _render_time_info(self, renderer, assets, ox, oy, cw, ch):
        if volume.is_volume_mode_active():
            return
        e, r = int(audio.get_elapsed_sec()), int(audio.get_remaining_sec())
        elapsed = f"{e // 60}:{e % 60:02d}"
        remaining = f"-{r // 60}:{r % 60:02d}"
        color = self._hex_rgb("000000")
        # Left: elapsed
        etex, ew, eh = assets.render_text(elapsed, color)
        if etex:
            dst = sdl2.SDL_Rect(ox + 8, oy + 94, ew, eh)
            sdl2.SDL_RenderCopy(renderer, etex, None, dst)
            sdl2.SDL_DestroyTexture(etex)
        # Right: remaining
        rtex, rw, rh = assets.render_text(remaining, color)
        if rtex:
            dst = sdl2.SDL_Rect(ox + cw - 8 - rw, oy + 94, rw, rh)
            sdl2.SDL_RenderCopy(renderer, rtex, None, dst)
            sdl2.SDL_DestroyTexture(rtex)

    # ---- Screen protocol ---------------------------------------------------

    def on_enter(self):
        self._scroll_offsets = {}

    def handle_input(self, event):
        if isinstance(event, ButtonPress):
            if event.button == Button.UP:
                return "back"
            if event.button == Button.DOWN:
                if event.long_press:
                    # Long press = stop playback and close
                    audio.stop()
                    return "back"
                # Short press = toggle play/pause
                ps = audio.get_play_state()
                audio.set_play_state("PAUSED" if ps == "PLAYING" else "PLAYING")
                return True
            if event.button == Button.CENTER:
                # Toggle play/pause
                ps = audio.get_play_state()
                audio.set_play_state("PAUSED" if ps == "PLAYING" else "PLAYING")
                return True
            if event.button == Button.LEFT:
                audio.set_elapsed_sec(0.0)
                return True
            if event.button == Button.RIGHT:
                audio.set_elapsed_sec(0.0)
                return True
        return False

    def render(self, renderer, assets, theme, viewport, dt=0.0):
        vx, vy, vw, vh = viewport

        btex, bw, bh = assets.get_texture("backdrop")
        if btex:
            # Full-screen backdrop — covers the entire canvas
            dst = sdl2.SDL_Rect(0, 0, 160, 128)
            sdl2.SDL_RenderCopy(renderer, btex, None, dst)
        else:
            bg = theme.get("colors", {}).get("background", "FFFFFF")
            bg_rgb = self._hex_rgb(bg)
            sdl2.SDL_SetRenderDrawColor(renderer, *bg_rgb, 255)
            sdl2.SDL_RenderFillRect(renderer, sdl2.SDL_Rect(vx, vy, vw, vh))

        self._render_content(renderer, assets, theme, viewport, dt)

    @staticmethod
    def _hex_rgb(h):
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    
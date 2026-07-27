"""Now Playing screen — iPod classic playback view.

Shows album art (or centered text when no art), track metadata,
progress bar, status bar icons, and a volume overlay when active.
"""

from . import Screen, ButtonPress, Button
from hardware import audio, battery, disk, input as hwinput, volume, settings as hwsettings, clock as hwclock
import sdl2


class NowPlayingScreen(Screen):
    """Full-screen Now Playing display with album art, track info, progress bar."""

    MARQUEE_SPEED_PX_S = 20
    MARQUEE_GAP_PX = 16

    def __init__(self):
        self._scroll_offsets = {}

    # ---- status bar helpers ------------------------------------------------

    def _render_status_bar(self, renderer, assets, theme, viewport):
        """Draw the top status bar: time, battery, playmode, disk, hold."""
        vx, vy, vw, vh = viewport
        sb_h = theme.get("statusbar", {}).get("height", 22)
        sb_color = theme.get("colors", {}).get("statusbar_text", "000000")
        sb_rgb = self._hex_rgb(sb_color)

        # Clock / status text (cycling every 10s)
        self._render_status_text(renderer, assets, vx, vy, vw, sb_h, sb_rgb)

        # Battery sprite
        self._render_battery(renderer, assets, vx, vy, vw, sb_h)

        # Playmode or disk sprite
        self._render_playmode_or_disk(renderer, assets, vx, vy, sb_h)

        # Hold icon
        if hwinput.is_hold_active() or hwinput.is_remote_hold_active():
            tex, tw, th = assets.get_texture("hold")
            if tex:
                dst = sdl2.SDL_Rect(vx + 24, vy + 4, tw, th)
                sdl2.SDL_RenderCopy(renderer, tex, None, dst)

    def _render_status_text(self, renderer, assets, vx, vy, vw, sb_h, color):
        import time
        # Cycle between status text and clock every 10 seconds
        t = int(time.time() * 10)  # 10-second cycle
        if t % 10 < 5:
            text = "Now Playing" if audio.is_audio_active() else "iPod"
        else:
            if hwclock.is_24h():
                text = f"{int(hwclock.get_hour()):02d}:{int(hwclock.get_minute()):02d}"
            else:
                h = int(hwclock.get_hour()) % 12 or 12
                ampm = "AM" if hwclock.get_hour() < 12 else "PM"
                text = f"{h}:{int(hwclock.get_minute()):02d} {ampm}"
        tex, tw, th = assets.render_text(text, color)
        if tex:
            cx = vx + vw // 2
            dst = sdl2.SDL_Rect(cx - tw // 2, vy + (sb_h - th) // 2, tw, th)
            sdl2.SDL_RenderCopy(renderer, tex, None, dst)
            sdl2.SDL_DestroyTexture(tex)

    def _render_battery(self, renderer, assets, vx, vy, vw, sb_h):
        tex, fw, fh, frames = assets.get_sprite("battery")
        if not tex:
            return
        if battery.is_charging():
            # Animate first 2 frames
            import time
            frame = int(time.time() * 2) % 2
        elif battery.is_charged_full():
            frame = 2
        else:
            bin_idx = min(21, int(battery.get_battery_percent() / 100 * 22))
            frame = 3 + bin_idx
        frame = max(0, min(frames - 1, frame))
        src = sdl2.SDL_Rect(0, frame * fh, fw, fh)
        dst = sdl2.SDL_Rect(vx + vw - fw - 2, vy + 4, fw, fh)
        sdl2.SDL_RenderCopy(renderer, tex, src, dst)

    def _render_playmode_or_disk(self, renderer, assets, vx, vy, sb_h):
        if disk.is_disk_active():
            tex, fw, fh, frames = assets.get_sprite("disk")
            if tex:
                import time
                frame = int(time.time() * 10) % frames
                src = sdl2.SDL_Rect(0, frame * fh, fw, fh)
                dst = sdl2.SDL_Rect(vx + 3, vy + 2, fw, fh)
                sdl2.SDL_RenderCopy(renderer, tex, src, dst)
        else:
            # Playmode icon
            tex, fw, fh, frames = assets.get_sprite("playmode")
            if tex:
                frame = {"PLAYING": 0, "PAUSED": 1, "FF": 2, "REW": 3}.get(audio.get_play_state(), 0)
                src = sdl2.SDL_Rect(0, frame * fh, fw, fh)
                dst = sdl2.SDL_Rect(vx + 4, vy + 5, fw, fh)
                sdl2.SDL_RenderCopy(renderer, tex, src, dst)

    # ---- content area ------------------------------------------------------

    def _render_content(self, renderer, assets, theme, viewport):
        vx, vy, vw, vh = viewport
        sb_h = theme.get("statusbar", {}).get("height", 22)
        cy = vy + sb_h  # content starts below status bar

        album_art_path = audio.get_album_art_path()

        if album_art_path:
            self._render_album_art_layout(renderer, assets, vx, cy, vw, vh - sb_h)
        else:
            self._render_no_art_layout(renderer, assets, vx, cy, vw, vh - sb_h)

        # Shuffle/repeat icons (top of content area)
        self._render_mode_indicators(renderer, assets, vx, cy + 2, vw)

        # Playlist position
        pos_text = f"{audio.get_playlist_pos()} of {audio.get_playlist_len()}"
        pos_color = self._hex_rgb(theme.get("colors", {}).get("secondary_text", "999999"))
        pos_tex, ptw, pth = assets.render_text(pos_text, pos_color)
        if pos_tex:
            dst = sdl2.SDL_Rect(vx + 11, cy + 18, ptw, pth)
            sdl2.SDL_RenderCopy(renderer, pos_tex, None, dst)
            sdl2.SDL_DestroyTexture(pos_tex)

        # Separator line above progress bar
        self._render_separator(renderer, vx, cy)

        # Progress bar at bottom
        self._render_progress_bar(renderer, assets, vx, cy, vw, vh - sb_h)

        # Elapsed / remaining time
        self._render_time_info(renderer, assets, vx, cy, vw, vh - sb_h)

    def _render_album_art_layout(self, renderer, assets, ox, oy, cw, ch):
        """Layout with album art on the left, info on the right."""
        # Album art — scale to fit within the 60 × 60 frame, preserving aspect ratio
        ART_SIZE = 60
        tex, tw, th = assets.get_dynamic_texture(
            audio.get_album_art_path(), max_size=(ART_SIZE, ART_SIZE),
        )
        if tex:
            # Centre non-square art within the frame
            art_x = ox + 8 + (ART_SIZE - tw) // 2
            art_y = oy + 34 + (ART_SIZE - th) // 2
            dst = sdl2.SDL_Rect(art_x, art_y, tw, th)
            sdl2.SDL_RenderCopy(renderer, tex, None, dst)

        # Art frame borders
        for name, x, y in [("aa_bottom", 6, 94), ("aa_left", 6, 34), ("aa_right", 68, 34)]:
            bt, bw, bh = assets.get_texture(name)
            if bt:
                dst = sdl2.SDL_Rect(ox + x, oy + y, bw, bh)
                sdl2.SDL_RenderCopy(renderer, bt, None, dst)

        # Track info, right of art (x=74, w=144)
        info_x = ox + 74
        info_w = 144
        text_color = self._hex_rgb("000000")
        items = [
            (audio.get_title() if audio.has_id3() else audio.get_filename(), 34),
            (audio.get_artist() if audio.has_id3() and audio.get_artist() else None, 52),
            (audio.get_album() if audio.has_id3() and audio.get_album() else None, 70),
        ]
        for text, y in items:
            if text is None:
                continue
            self._draw_marquee_text(renderer, assets, text, info_x, oy + y, info_w, text_color, id(text))

    def _render_no_art_layout(self, renderer, assets, ox, oy, cw, ch):
        """Layout centered text when no album art."""
        text_color = self._hex_rgb("000000")
        items = [
            (audio.get_title() if audio.has_id3() else audio.get_filename(), 34),
            (audio.get_artist() if audio.has_id3() and audio.get_artist() else None, 58),
            (audio.get_album() if audio.has_id3() and audio.get_album() else None, 82),
        ]
        for text, y in items:
            if text is None:
                continue
            self._draw_marquee_text(renderer, assets, text, ox, oy + y, 220, text_color, id(text), center=True)

    def _draw_marquee_text(self, renderer, assets, text, x, y, w, color, key, center=False):
        tex, tw, th = assets.render_text(text, color)
        if not tex:
            return
        if tw <= w:
            dx = x + (w - tw) // 2 if center else x
            dst = sdl2.SDL_Rect(int(dx), int(y), int(tw), int(th))
            sdl2.SDL_RenderCopy(renderer, tex, None, dst)
        else:
            # Marquee scroll
            total = tw + self.MARQUEE_GAP_PX
            offset = self._scroll_offsets.get(key, 0.0)
            import time
            dt = 1/60  # approximate
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
        """Shuffle and repeat icons."""
        if hwsettings.get_repeat_mode() != "OFF":
            tex, fw, fh, frames = assets.get_sprite("repeat")
            if tex:
                frame = {"ALL": 0, "ONE": 1, "AB": 2, "SHUFFLE": 3}.get(hwsettings.get_repeat_mode(), 0)
                src = sdl2.SDL_Rect(0, frame * fh, fw, fh)
                dst = sdl2.SDL_Rect(ox + 177, oy, fw, fh)
                sdl2.SDL_RenderCopy(renderer, tex, src, dst)
        if hwsettings.is_shuffle_enabled():
            tex, fw, fh, _ = assets.get_sprite("shuffle")
            if tex:
                dst = sdl2.SDL_Rect(ox + 193, oy, fw, fh)
                sdl2.SDL_RenderCopy(renderer, tex, None, dst)

    def _render_separator(self, renderer, ox, oy):
        """Thin horizontal line above the progress bar, like the real iPod."""
        sdl2.SDL_SetRenderDrawColor(renderer, 180, 180, 180, 255)
        sdl2.SDL_RenderDrawLine(renderer, ox + 8, oy + 98, ox + 212, oy + 98)

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
        x, y = ox + 12, oy + 104
        fill_w = int(196 * value)
        if fill_w > 0:
            src = sdl2.SDL_Rect(0, 0, int(iw * value), ih)
            dst = sdl2.SDL_Rect(x, y, fill_w, 10)
            sdl2.SDL_RenderCopy(renderer, tex, src, dst)

        # Volume mode left/right icons
        if volume.is_volume_mode_active():
            il, _, _ = assets.get_texture("vol_left")
            if il:
                sdl2.SDL_RenderCopy(renderer, il, None, sdl2.SDL_Rect(ox + 4, oy + 101, 0, 0))
            ir, _, _ = assets.get_texture("vol_right")
            if ir:
                sdl2.SDL_RenderCopy(renderer, ir, None, sdl2.SDL_Rect(ox + 193, oy + 101, 0, 0))

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
            dst = sdl2.SDL_Rect(ox + 11, oy + 120, ew, eh)
            sdl2.SDL_RenderCopy(renderer, etex, None, dst)
            sdl2.SDL_DestroyTexture(etex)
        # Right: remaining
        rtex, rw, rh = assets.render_text(remaining, color)
        if rtex:
            dst = sdl2.SDL_Rect(ox + 209 - rw, oy + 120, rw, rh)
            sdl2.SDL_RenderCopy(renderer, rtex, None, dst)
            sdl2.SDL_DestroyTexture(rtex)

    # ---- Screen protocol ---------------------------------------------------

    def on_enter(self):
        self._scroll_offsets = {}

    def handle_input(self, event):
        if isinstance(event, ButtonPress):
            if event.button == Button.UP:
                return "back"
            if event.button in (Button.CENTER, Button.DOWN):
                # Toggle play/pause
                ps = audio.get_play_state()
                audio.set_play_state("PAUSED" if ps == "PLAYING" else "PLAYING")
                return True
            if event.button == Button.LEFT:
                # Rewind / previous track (stub: reset elapsed)
                audio.set_elapsed_sec(0.0)
                return True
            if event.button == Button.RIGHT:
                # Forward / next track (stub: reset elapsed)
                audio.set_elapsed_sec(0.0)
                return True
        return False

    def render(self, renderer, assets, theme, viewport):
        vx, vy, vw, vh = viewport

        # Background
        bg = theme.get("colors", {}).get("background", "FFFFFF")
        bg_rgb = self._hex_rgb(bg)
        sdl2.SDL_SetRenderDrawColor(renderer, *bg_rgb, 255)
        sdl2.SDL_RenderFillRect(renderer, sdl2.SDL_Rect(vx, vy, vw, vh))

        self._render_status_bar(renderer, assets, theme, viewport)
        self._render_content(renderer, assets, theme, viewport)

    @staticmethod
    def _hex_rgb(h):
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
"""Now Playing screen — iPod classic playback view.

Shows album art (or centered text when no art), track metadata,
progress bar, and time info.  Compact layout for the 160×128 canvas.

Album art is read from the audio file's embedded metadata by default.
When no embedded art exists, the backup cover from the library config
is used instead.

Modes
-----
Normal     — scroll changes volume (volume bar auto-hides after 3 s)
Scrub      — scroll seeks through the track (◇ on the progress bar)
           — CENTER toggles between Normal and Scrub
           — CENTER while volume bar is visible returns to Normal
           — leaving scrub mode seeks the audio to the chosen position
"""

import os
import tempfile

from . import Screen, ButtonPress, ScrollEvent, Button
from hardware import audio, volume, settings as hwsettings
import sdl2

_COVER_CACHE = os.path.join(tempfile.gettempdir(), "nupod_covers")


class NowPlayingScreen(Screen):
    """Full-screen Now Playing display with album art, track info, progress bar."""

    @property
    def title(self):
        return "Now Playing"

    MARQUEE_SPEED_PX_S = 20
    MARQUEE_GAP_PX = 16

    def __init__(self):
        self._scroll_offsets = {}
        self._scrub_mode = False
        self._scrub_pos = 0.0  # position in seconds during scrub mode

    @staticmethod
    def _get_cover_path() -> str | None:
        """Return a path to cover art to display.

        Priority:
          1. Embedded cover art extracted from the current audio file
          2. Backup cover image from the library config

        Embedded art is extracted once and cached to a temp file so SDL
        can load it as a texture on subsequent frames.
        """
        audio_file = audio.get_current_filepath()
        if audio_file and os.path.exists(audio_file):
            os.makedirs(_COVER_CACHE, exist_ok=True)
            cache_path = os.path.join(_COVER_CACHE, os.path.basename(audio_file) + ".jpg")
            if os.path.exists(cache_path):
                return cache_path
            try:
                import mutagen
                import base64
                mf = mutagen.File(audio_file)
                if mf is not None:
                    picture = None
                    if hasattr(mf, "tags") and mf.tags:
                        for key in mf.tags.keys():
                            if key.startswith("APIC:"):
                                picture = mf.tags[key].data
                                break
                    if picture is None and "covr" in mf:
                        raw = mf["covr"]
                        if isinstance(raw, list):
                            raw = raw[0]
                        picture = bytes(raw)
                    if picture is None and hasattr(mf, "pictures") and mf.pictures:
                        picture = mf.pictures[0].data
                    if picture is None and "metadata_block_picture" in mf:
                        raw = mf["metadata_block_picture"]
                        if isinstance(raw, list):
                            raw = raw[0]
                        from mutagen.flac import Picture
                        pic = Picture(base64.b64decode(raw))
                        picture = pic.data
                    if picture:
                        with open(cache_path, "wb") as f:
                            f.write(picture)
                        return cache_path
            except ImportError:
                pass
            except Exception:
                pass
        backup = audio.get_album_art_path()
        if backup and os.path.exists(backup):
            return backup
        return None

    # ---- content area ------------------------------------------------------

    def _render_content(self, renderer, assets, theme, viewport, dt=1/60):
        vx, vy, vw, vh = viewport
        cy = vy

        cover_path = self._get_cover_path()
        if cover_path:
            self._render_album_art_layout(renderer, assets, vx, cy, vw, vh, cover_path, dt)
        else:
            self._render_no_art_layout(renderer, assets, vx, cy, vw, vh, dt)

        self._render_mode_indicators(renderer, assets, vx, cy + 2, vw)

        pos_text = f"{audio.get_queue_pos() + 1} of {audio.get_queue_len()}"
        pos_color = self._hex_rgb(theme.get("colors", {}).get("secondary_text", "999999"))
        pos_tex, ptw, pth = assets.render_text(pos_text, pos_color)
        if pos_tex:
            dst = sdl2.SDL_Rect(vx + 4, cy + 2, ptw, pth)
            sdl2.SDL_RenderCopy(renderer, pos_tex, None, dst)
            sdl2.SDL_DestroyTexture(pos_tex)

        self._render_separator(renderer, vx, cy, vw)
        self._render_progress_bar(renderer, assets, vx, cy, vw, vh)
        self._render_time_info(renderer, assets, vx, cy, vw, vh)

    def _render_album_art_layout(self, renderer, assets, ox, oy, cw, ch, cover_path, dt=1/60):
        ART_SIZE = 50
        try:
            tex, tw, th = assets.get_dynamic_texture(cover_path, max_size=(ART_SIZE, ART_SIZE))
        except Exception:
            tex = None
        if tex:
            art_x = ox + 5 + (ART_SIZE - tw) // 2
            art_y = oy + 18 + (ART_SIZE - th) // 2
            dst = sdl2.SDL_Rect(art_x, art_y, tw, th)
            sdl2.SDL_RenderCopy(renderer, tex, None, dst)

        info_x = ox + 60
        info_w = cw - 65
        text_color = self._hex_rgb("000000")
        items = [
            (audio.get_title() if bool(audio.get_title().strip()) else audio.get_filename(), 20),
            (audio.get_artist() if bool(audio.get_title().strip()) and audio.get_artist() else None, 40),
            (audio.get_album() if bool(audio.get_title().strip()) and audio.get_album() else None, 56),
        ]
        for text, y in items:
            if text is None:
                continue
            self._draw_marquee_text(renderer, assets, text, info_x, oy + y, info_w, text_color, id(text), dt=dt)

    def _render_no_art_layout(self, renderer, assets, ox, oy, cw, ch, dt=1/60):
        text_color = self._hex_rgb("000000")
        items = [
            (audio.get_title() if bool(audio.get_title().strip()) else audio.get_filename(), 20),
            (audio.get_artist() if bool(audio.get_title().strip()) and audio.get_artist() else None, 40),
            (audio.get_album() if bool(audio.get_title().strip()) and audio.get_album() else None, 56),
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
        sdl2.SDL_SetRenderDrawColor(renderer, 180, 180, 180, 255)
        sdl2.SDL_RenderDrawLine(renderer, ox + 8, oy + 76, ox + cw - 8, oy + 76)

    def _render_progress_bar(self, renderer, assets, ox, oy, cw, ch):
        x, y = ox + 9, oy + 78
        bar_w = 142
        bar_h = 6

        if volume.is_volume_mode_active() and not self._scrub_mode:
            # Volume bar
            value = volume.get_volume_percent() / 100.0
            fill_w = max(1, int(bar_w * value))
            sdl2.SDL_SetRenderDrawColor(renderer, 200, 200, 200, 255)
            sdl2.SDL_RenderFillRect(renderer, sdl2.SDL_Rect(x, y, bar_w, bar_h))
            sdl2.SDL_SetRenderDrawColor(renderer, 120, 120, 120, 255)
            sdl2.SDL_RenderFillRect(renderer, sdl2.SDL_Rect(x, y, fill_w, bar_h))
            il, ilw, ilh = assets.get_texture("vol_left")
            if il:
                sdl2.SDL_RenderCopy(renderer, il, None, sdl2.SDL_Rect(ox + 4, oy + 77, ilw, ilh))
            ir, irw, irh = assets.get_texture("vol_right")
            if ir:
                sdl2.SDL_RenderCopy(renderer, ir, None, sdl2.SDL_Rect(ox + cw - 4 - irw, oy + 77, irw, irh))
            return

        # Progress bar (texture)
        tex, iw, ih = assets.get_texture("progress_bar")
        if not tex:
            return

        if self._scrub_mode:
            value = self._scrub_pos / audio.get_track_length_sec() if audio.get_track_length_sec() > 0 else 0.0
        else:
            value = audio.get_track_progress()

        src_w = int(iw * value)
        dst_w = int(bar_w * value)
        if audio.is_audio_active():
            src_w = max(1, src_w)
            dst_w = max(1, dst_w)
        if src_w > 0 and dst_w > 0:
            src = sdl2.SDL_Rect(0, 0, src_w, ih)
            dst = sdl2.SDL_Rect(x, y, dst_w, bar_h)
            sdl2.SDL_RenderCopy(renderer, tex, src, dst)

            # Diamond playhead in scrub mode
            if self._scrub_mode:
                diamond_x = x + dst_w - 1  # right edge of fill
                # Draw a small diamond (4x4 px)
                sdl2.SDL_SetRenderDrawColor(renderer, 50, 50, 50, 255)
                sdl2.SDL_RenderDrawLine(renderer, diamond_x, y - 2, diamond_x + 2, y + 3)
                sdl2.SDL_RenderDrawLine(renderer, diamond_x, y - 2, diamond_x - 2, y + 3)
                sdl2.SDL_RenderDrawLine(renderer, diamond_x + 2, y + 3, diamond_x, y + 8)
                sdl2.SDL_RenderDrawLine(renderer, diamond_x - 2, y + 3, diamond_x, y + 8)

    def _render_time_info(self, renderer, assets, ox, oy, cw, ch):
        if volume.is_volume_mode_active() and not self._scrub_mode:
            return

        if self._scrub_mode:
            e = int(self._scrub_pos)
        else:
            e = int(audio.get_elapsed_sec())
        r = int(audio.get_track_length_sec()) - e

        elapsed = f"{e // 60}:{e % 60:02d}"
        remaining = f"-{r // 60}:{r % 60:02d}"
        color = self._hex_rgb("000000")
        etex, ew, eh = assets.render_text(elapsed, color)
        if etex:
            dst = sdl2.SDL_Rect(ox + 8, oy + 94, ew, eh)
            sdl2.SDL_RenderCopy(renderer, etex, None, dst)
            sdl2.SDL_DestroyTexture(etex)
        rtex, rw, rh = assets.render_text(remaining, color)
        if rtex:
            dst = sdl2.SDL_Rect(ox + cw - 8 - rw, oy + 94, rw, rh)
            sdl2.SDL_RenderCopy(renderer, rtex, None, dst)
            sdl2.SDL_DestroyTexture(rtex)

    # ---- Screen protocol ---------------------------------------------------

    def on_enter(self):
        self._scroll_offsets = {}
        self._scrub_mode = False
        self._scrub_pos = 0.0

    def handle_input(self, event):
        if isinstance(event, ScrollEvent):
            if self._scrub_mode:
                # Adjust scrub position locally — don't seek yet
                length = audio.get_track_length_sec()
                if length > 0:
                    step = 5.0
                    if event.direction < 0:  # CCW = forward
                        self._scrub_pos = min(length, self._scrub_pos + step)
                    else:  # CW = backward
                        self._scrub_pos = max(0.0, self._scrub_pos - step)
                return True
            else:
                pct = volume.get_volume_percent()
                step = 2.0
                if event.direction < 0:
                    volume.set_volume_percent(pct + step)
                else:
                    volume.set_volume_percent(pct - step)
                volume.trigger_volume_change()
                # Sync mpv volume in real-time
                audio.set_volume(volume.get_volume_percent())
                return True

        if isinstance(event, ButtonPress):
            btn = event.button
            if btn == Button.UP:
                # If in scrub mode, seek before leaving
                if self._scrub_mode:
                    audio.seek_to(self._scrub_pos)
                return "back"

            if btn == Button.DOWN:
                if event.long_press:
                    audio.stop()
                    return "back"
                ps = audio.get_play_state()
                audio.set_play_state("PAUSED" if ps == "PLAYING" else "PLAYING")
                return True

            if btn == Button.CENTER:
                if volume.is_volume_mode_active():
                    volume.clear_volume_mode()
                    return True  # Don't enter scrub — just return to normal

                if self._scrub_mode:
                    # Exit scrub mode → seek to chosen position
                    audio.seek_to(self._scrub_pos)
                    self._scrub_mode = False
                else:
                    # Enter scrub mode → capture current position
                    self._scrub_pos = audio.get_elapsed_sec()
                    self._scrub_mode = True
                return True

            if btn == Button.LEFT:
                audio.prev_track()
                return True
            if btn == Button.RIGHT:
                audio.next_track()
                return True
        return False

    def render(self, renderer, assets, theme, viewport, dt=0.0):
        # BackdropPlay.bmp covers the full canvas and already has the
        # status bar background and progress bar track baked in.
        btex, bw, bh = assets.get_texture("backdrop_play")
        if btex:
            dst = sdl2.SDL_Rect(0, 0, 160, 128)
            sdl2.SDL_RenderCopy(renderer, btex, None, dst)

        self._render_content(renderer, assets, theme, viewport, dt)

    @staticmethod
    def _hex_rgb(h):
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
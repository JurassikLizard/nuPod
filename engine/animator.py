"""
Smooth slide animation system for menu transitions.

Renders both old and new states to textures, then animates between them
with a smoothstep easing curve. The old state slides out with a fade
while the new state slides in from the opposite side.

Push (going deeper):
  old → slides left, fades out
  new → slides in from the right

Pop (going back):
  old → slides right, fades out
  new → slides in from the left
"""

from __future__ import annotations

import sdl2


class Animator:
    """Handles push/pop slide transitions between UI states."""

    def __init__(self, renderer, canvas_w, canvas_h, bg_color=(0, 0, 0)):
        self.renderer = renderer
        self.cw = canvas_w
        self.ch = canvas_h
        self.bg_color = bg_color

        self.active = False
        self.old_tex = None
        self.new_tex = None
        self.elapsed = 0.0
        self.duration = 0.2  # seconds — slightly longer for smoother feel
        self.direction = -1  # -1 = push (go deeper), +1 = pop (go back)

    # ── Public API ───────────────────────────────────────────────────────────

    def start_push(self, old_render_func):
        """Start a push (slide-left) animation by capturing the old state.

        After the state transition, call *capture_new()* with the new render func.
        """
        self._render_to_texture(old_render_func, is_old=True)
        self.direction = -1
        self.elapsed = 0.0
        self.active = True

    def start_pop(self, old_render_func):
        """Start a pop (slide-right) animation by capturing the old state."""
        self._render_to_texture(old_render_func, is_old=True)
        self.direction = 1
        self.elapsed = 0.0
        self.active = True

    def start_pop_with_texture(self, old_texture):
        """Start a pop animation with a pre-rendered old texture."""
        self._cleanup_old()
        self.old_tex = old_texture
        self.direction = 1
        self.elapsed = 0.0
        self.active = True

    def capture_new(self, new_render_func):
        """Capture the new state after the transition has occurred."""
        self._render_to_texture(new_render_func, is_old=False)

    def render(self, dt):
        """Render the current animation frame. Returns True while animating,
        False when the animation has completed."""
        if not self.active:
            return False

        self.elapsed += dt
        if self.elapsed >= self.duration or self.old_tex is None:
            self.active = False
            self._cleanup()
            return False

        # Smoothstep: t²(3 - 2t) — much smoother start/stop than ease-out quad
        t = self.elapsed / self.duration
        t = t * t * (3.0 - 2.0 * t)

        # Fill background so alpha-faded old content reveals the theme bg, not black
        sdl2.SDL_SetRenderDrawColor(self.renderer, *self.bg_color, 255)
        sdl2.SDL_RenderClear(self.renderer)
        sdl2.SDL_RenderFillRect(self.renderer, sdl2.SDL_Rect(0, 0, self.cw, self.ch))

        # Old content: slides out with fade
        if self.old_tex:
            offset = -int(t * self.cw) if self.direction < 0 else int(t * self.cw)
            alpha = max(0, min(255, int(255 * (1.0 - t))))
            sdl2.SDL_SetTextureAlphaMod(self.old_tex, alpha)
            dst = sdl2.SDL_Rect(offset, 0, self.cw, self.ch)
            sdl2.SDL_RenderCopy(self.renderer, self.old_tex, None, dst)
            sdl2.SDL_SetTextureAlphaMod(self.old_tex, 255)

        # New content: slides in from the opposite side
        if self.new_tex:
            if self.direction < 0:
                # Push: new slides in from the right
                new_offset = int((1.0 - t) * self.cw)
            else:
                # Pop: new slides in from the left
                new_offset = -int((1.0 - t) * self.cw)
            dst = sdl2.SDL_Rect(new_offset, 0, self.cw, self.ch)
            sdl2.SDL_RenderCopy(self.renderer, self.new_tex, None, dst)

        return True

    # ── Internal ─────────────────────────────────────────────────────────────

    def _render_to_texture(self, render_func, is_old=True):
        """Render *render_func* into a target texture and store it."""
        tex = sdl2.SDL_CreateTexture(
            self.renderer,
            sdl2.SDL_PIXELFORMAT_RGBA8888,
            sdl2.SDL_TEXTUREACCESS_TARGET,
            self.cw, self.ch,
        )
        if not tex:
            return

        # Enable alpha blending on the texture so alpha modulation works
        sdl2.SDL_SetTextureBlendMode(tex, sdl2.SDL_BLENDMODE_BLEND)

        sdl2.SDL_SetRenderTarget(self.renderer, tex)
        render_func()
        sdl2.SDL_SetRenderTarget(self.renderer, None)

        if is_old:
            self._cleanup_old()
            self.old_tex = tex
        else:
            self._cleanup_new()
            self.new_tex = tex

    def _cleanup(self):
        self._cleanup_old()
        self._cleanup_new()

    def _cleanup_old(self):
        if self.old_tex:
            sdl2.SDL_DestroyTexture(self.old_tex)
            self.old_tex = None

    def _cleanup_new(self):
        if self.new_tex:
            sdl2.SDL_DestroyTexture(self.new_tex)
            self.new_tex = None
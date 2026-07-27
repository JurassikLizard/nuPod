import os
import sdl2
import sdl2.sdlimage as sdlimage
import sdl2.sdlttf as sdlttf

TRANSPARENT_KEY = (0xFF, 0x00, 0xFF)  # Rockbox magenta color-key convention


class AssetManager:
    def __init__(self, renderer, theme_config, theme_dir, scale=1):
        self.renderer = renderer
        self.root = os.path.join(theme_dir, theme_config.get("assets_root", "assets"))
        self._images_cfg = theme_config["images"]
        self._textures = {}
        self._sprites = {}
        self._dynamic = {}
        self.scale = max(1, scale)

        font_cfg = theme_config["font"]
        font_path = os.path.join(theme_dir, font_cfg["path"])
        if not os.path.exists(font_path):
            raise RuntimeError(f"Font not found: {font_path}")

        base_size = font_cfg.get("size", 10)
        # Rendered at `scale`x so glyphs are native-resolution at the window's
        # pixel density, not stretched up from a tiny canvas-resolution bitmap.
        self.font = sdlttf.TTF_OpenFont(font_path.encode(), base_size * self.scale)
        if not self.font:
            raise RuntimeError(
                f"TTF_OpenFont failed for {font_path}: {sdlttf.TTF_GetError().decode()}"
            )

        fg = theme_config.get("colors", {}).get("foreground", "000000")
        self.default_color = tuple(int(fg[i:i + 2], 16) for i in (0, 2, 4))

    def _load_surface(self, path):
        surf = sdlimage.IMG_Load(path.encode())
        if not surf:
            raise RuntimeError(f"Failed to load image: {path} ({sdl2.SDL_GetError()})")
        return surf

    def _texture_from_surface(self, surf, colorkey=True):
        """Converts a surface to a texture, applying Rockbox's magenta
        transparency convention and forcing correct alpha blending."""
        if colorkey:
            fmt = surf.contents.format
            magenta = sdl2.SDL_MapRGB(fmt, *TRANSPARENT_KEY)
            sdl2.SDL_SetColorKey(surf, sdl2.SDL_TRUE, magenta)
        tex = sdl2.SDL_CreateTextureFromSurface(self.renderer, surf)
        sdl2.SDL_SetTextureBlendMode(tex, sdl2.SDL_BLENDMODE_BLEND)
        return tex

    def get_texture(self, name):
        if name not in self._textures:
            cfg = self._images_cfg[name]
            surf = self._load_surface(os.path.join(self.root, cfg["path"]))
            w, h = surf.contents.w, surf.contents.h
            tex = self._texture_from_surface(surf)
            sdl2.SDL_FreeSurface(surf)
            self._textures[name] = (tex, w, h)
        return self._textures[name]

    def get_sprite(self, name):
        """Returns (texture, frame_w, frame_h, frame_count). Frames are
        stacked vertically in the source bitmap, one Rockbox WPS convention."""
        if name not in self._sprites:
            cfg = self._images_cfg[name]
            frames = cfg.get("frames", 1)
            surf = self._load_surface(os.path.join(self.root, cfg["path"]))
            w, h = surf.contents.w, surf.contents.h
            tex = self._texture_from_surface(surf)
            sdl2.SDL_FreeSurface(surf)
            self._sprites[name] = (tex, w, h // frames, frames)
        return self._sprites[name]

    def get_dynamic_texture(self, path, max_size=None):
        """For content loaded at runtime (album art). No color-key applied —
        real photos may legitimately contain magenta pixels.

        If *max_size* is ``(max_w, max_h)`` the image is scaled proportionally
        to fit within those bounds.  The returned ``(tex, w, h)`` reflects the
        scaled size (or the original size if no scaling was needed).
        """
        cache_key = (path, max_size) if max_size else path
        if cache_key not in self._dynamic:
            surf = self._load_surface(path)
            w, h = surf.contents.w, surf.contents.h

            if max_size:
                max_w, max_h = max_size
                scale = min(max_w / w, max_h / h)
                if scale < 1.0:
                    new_w = max(1, int(w * scale))
                    new_h = max(1, int(h * scale))
                    # Create a target surface with the same pixel format as the
                    # source so that SDL_BlitScaled doesn't need to convert.
                    fmt = surf.contents.format.contents
                    new_surf = sdl2.SDL_CreateRGBSurface(
                        0, new_w, new_h, fmt.BitsPerPixel,
                        fmt.Rmask, fmt.Gmask, fmt.Bmask, fmt.Amask,
                    )
                    if new_surf:
                        sdl2.SDL_BlitScaled(surf, None, new_surf, None)
                        sdl2.SDL_FreeSurface(surf)
                        surf = new_surf
                        w, h = new_w, new_h

            tex = self._texture_from_surface(surf, colorkey=False)
            sdl2.SDL_FreeSurface(surf)
            self._dynamic[cache_key] = (tex, w, h)
        return self._dynamic[cache_key]

    def render_text(self, text, color=None):
        if not text:
            return None, 0, 0
        color = color or self.default_color
        sdl_color = sdl2.SDL_Color(color[0], color[1], color[2], 255)
        surf = sdlttf.TTF_RenderUTF8_Blended(self.font, text.encode("utf-8"), sdl_color)
        if not surf:
            return None, 0, 0
        w, h = surf.contents.w, surf.contents.h
        tex = self._texture_from_surface(surf, colorkey=False)
        sdl2.SDL_FreeSurface(surf)
        # Texture is native-resolution (rendered at `scale`x). Report
        # logical-space dimensions so layout math (wrapping, centering,
        # marquee) stays in canvas coordinates; the renderer's own
        # logical->window upscale brings it back to 1:1 physical pixels.
        return tex, int(w / self.scale), int(h / self.scale)
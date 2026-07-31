"""
iPod Classic emulator — main entry point.

Uses a hardware-abstraction layer where each subsystem is a module of
getter/setter functions.  All code imports hardware modules directly.
"""

import os
import sys
import json
import time

import sdl2
import sdl2.sdlttf as sdlttf
import sdl2.sdlimage as sdlimage

from engine.assets import AssetManager
from engine.input import KeyboardInputStub, ButtonPress, ScrollEvent, Button
from engine.menu import MenuController, MenuRenderer
from engine.screen_manager import ScreenManager
from engine.menu_tree import build_main_menu
from engine.animator import Animator
from engine.screens.now_playing import NowPlayingScreen

# Hardware API — functional modules
from hardware import battery
from hardware import clock as hwclock
from hardware import disk
from hardware import audio
from hardware import volume
from hardware import display
from hardware import storage
from hardware import settings
from hardware import input as hwinput


THEME_DIR = os.path.join(os.path.dirname(__file__), "theme")


def load_json(name):
    with open(os.path.join(THEME_DIR, name)) as f:
        return json.load(f)


def hex_rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# The status-bar icon sprites carry a few blank rows, so centering on the
# full frame height pushes their visible glyphs below the 20px title bar.
# Negative padding pulls them up, leaving that blank space above the bar.
STATUSBAR_ICON_VPAD = -2


def render_status_bar(renderer, assets, theme, title):
    """Draw the iPod classic status bar: title (center), battery (right),
    playmode/disk (left).  No background fill — the backdrop has it baked in."""
    sb = theme.get("statusbar", {})
    sb_h = sb.get("height", 20)
    canvas_w = theme["canvas"]["width"]

    text_color = hex_rgb(theme.get("colors", {}).get("statusbar_text", "000000"))

    # Title text (center)
    tex, tw, th = assets.render_text(title, text_color)
    if tex:
        tw, th = int(tw), int(th)
        cx = (canvas_w - tw) // 2
        dst = sdl2.SDL_Rect(cx, (sb_h - th) // 2, tw, th)
        sdl2.SDL_RenderCopy(renderer, tex, None, dst)
        sdl2.SDL_DestroyTexture(tex)

    # Battery sprite (right side)
    try:
        btex, bfw, bfh, bframes = assets.get_sprite("battery")
        if btex:
            if battery.is_charging():
                frame = int(time.time() * 2) % 2
            elif battery.is_charged_full():
                frame = 2
            else:
                frame = 3 + min(21, int(battery.get_battery_percent() / 100 * 22))
            frame = max(0, min(bframes - 1, frame))
            src = sdl2.SDL_Rect(0, frame * bfh, bfw, bfh)
            dst = sdl2.SDL_Rect(canvas_w - bfw - 2, (sb_h - bfh) // 2 + STATUSBAR_ICON_VPAD, bfw, bfh)
            sdl2.SDL_RenderCopy(renderer, btex, src, dst)
    except Exception:
        pass

    # Playmode / disk sprite (left side)
    try:
        play_state = audio.get_play_state()
        if play_state == "STOPPED":
            # No icon when nothing is playing — clean and realistic
            pass
        elif disk.is_disk_active():
            # Static disk icon during actual disk access (no animation)
            dtex, dfw, dfh, _ = assets.get_sprite("disk")
            if dtex:
                dst = sdl2.SDL_Rect(3, (sb_h - dfh) // 2 + STATUSBAR_ICON_VPAD, dfw, dfh)
                sdl2.SDL_RenderCopy(renderer, dtex, None, dst)
        else:
            # Playmode icon based on current state
            ptex, pfw, pfh, pframes = assets.get_sprite("playmode")
            if ptex:
                frame = {"PLAYING": 0, "PAUSED": 1, "FF": 2, "REW": 3}.get(play_state, 0)
                src = sdl2.SDL_Rect(0, frame * pfh, pfw, pfh)
                dst = sdl2.SDL_Rect(4, (sb_h - pfh) // 2 + STATUSBAR_ICON_VPAD, pfw, pfh)
                sdl2.SDL_RenderCopy(renderer, ptex, src, dst)

                # "L" indicator for local mode, to the right of the playmode icon
                if audio.is_local():
                    ltex, lw, lh = assets.render_text("L", text_color)
                    if ltex:
                        lx = 4 + pfw + 2
                        ldst = sdl2.SDL_Rect(lx, (sb_h - lh) // 2 + STATUSBAR_ICON_VPAD, lw, lh)
                        sdl2.SDL_RenderCopy(renderer, ltex, None, ldst)
                        sdl2.SDL_DestroyTexture(ltex)
    except Exception:
        pass


def main():
    sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO)
    sdlttf.TTF_Init()
    sdlimage.IMG_Init(sdlimage.IMG_INIT_PNG | sdlimage.IMG_INIT_JPG)

    theme = load_json("theme.json")

    cw, ch = theme["canvas"]["width"], theme["canvas"]["height"]
    ww, wh = theme["window"]["width"], theme["window"]["height"]
    scale = max(1, round(min(ww / cw, wh / ch)))

    sdl2.SDL_SetHint(sdl2.SDL_HINT_RENDER_SCALE_QUALITY, b"0")

    window = sdl2.SDL_CreateWindow(
        b"iPod Classic",
        sdl2.SDL_WINDOWPOS_CENTERED, sdl2.SDL_WINDOWPOS_CENTERED,
        ww, wh, sdl2.SDL_WINDOW_SHOWN,
    )
    renderer = sdl2.SDL_CreateRenderer(
        window, -1, sdl2.SDL_RENDERER_ACCELERATED | sdl2.SDL_RENDERER_PRESENTVSYNC
    )
    sdl2.SDL_RenderSetLogicalSize(renderer, cw, ch)

    assets = AssetManager(renderer, theme, THEME_DIR, scale)

    colors = theme["colors"]
    bg_rgb = hex_rgb(colors["background"])
    sb_h = theme.get("statusbar", {}).get("height", 20)
    content_vp = (0, sb_h, cw, ch - sb_h)

    menu_style = {
        "row_height": 18,
        "text_color": hex_rgb(colors["foreground"]),
        "background_color": hex_rgb(colors["background"]),
        "selector_start": hex_rgb(colors["selector_start"]),
        "selector_end": hex_rgb(colors["selector_end"]),
        "selector_text_color": hex_rgb(colors["selector_text"]),
        "secondary_text_color": hex_rgb(colors.get("secondary_text", "999999")),
    }

    input_stub = KeyboardInputStub()
    running = [True]

    # Animation system
    animator = Animator(renderer, cw, ch, bg_color=bg_rgb)

    # ── Render helpers for animation capture (full-canvas textures) ────

    def _capture_menu():
        """Render the current menu state (full canvas with status bar + backdrop)."""
        title = menu.stack[-1].title if menu.stack else ""
        btex, bw, bh = assets.get_texture("backdrop")
        if btex:
            sdl2.SDL_RenderCopy(renderer, btex, None, sdl2.SDL_Rect(0, 0, 160, 128))
        else:
            sdl2.SDL_SetRenderDrawColor(renderer, *bg_rgb, 255)
            sdl2.SDL_RenderClear(renderer)
        render_status_bar(renderer, assets, theme, title)
        MenuRenderer(renderer, assets, menu_style, content_vp).render(menu)

    def _capture_screen():
        """Render the current screen state (full canvas with status bar)."""
        if screen_manager.active and isinstance(screen_manager._screen, NowPlayingScreen):
            sdl2.SDL_SetRenderDrawColor(renderer, *bg_rgb, 255)
            sdl2.SDL_RenderClear(renderer)
        else:
            btex, bw, bh = assets.get_texture("backdrop")
            if btex:
                sdl2.SDL_RenderCopy(renderer, btex, None, sdl2.SDL_Rect(0, 0, 160, 128))
            else:
                sdl2.SDL_SetRenderDrawColor(renderer, *bg_rgb, 255)
                sdl2.SDL_RenderClear(renderer)
        screen_manager.render(renderer, assets, theme, content_vp, dt)
        render_status_bar(renderer, assets, theme, screen_manager.title)

    # ── Main render function ──────────────────────────────────────────

    def render():
        if animator.active:
            return animator.render(dt)

        # Backdrop.bmp has the status bar background baked in.
        # Render it for everything except the Now Playing screen
        # (which uses BackdropPlay.bmp instead).
        if screen_manager.active and isinstance(screen_manager._screen, NowPlayingScreen):
            sdl2.SDL_SetRenderDrawColor(renderer, *bg_rgb, 255)
            sdl2.SDL_RenderClear(renderer)
        else:
            btex, bw, bh = assets.get_texture("backdrop")
            if btex:
                dst = sdl2.SDL_Rect(0, 0, 160, 128)
                sdl2.SDL_RenderCopy(renderer, btex, None, dst)
            else:
                sdl2.SDL_SetRenderDrawColor(renderer, *bg_rgb, 255)
                sdl2.SDL_RenderClear(renderer)

        # Content below status bar
        if screen_manager.active:
            screen_manager.render(renderer, assets, theme, content_vp, dt)
            # Status bar on top — screens render their own backdrop which
            # would otherwise cover the text/icons.
            render_status_bar(renderer, assets, theme, screen_manager.title)
        else:
            # For menus, backdrop has the status bar background baked in
            current_title = menu.stack[-1].title if menu.stack else ""
            render_status_bar(renderer, assets, theme, current_title)
            MenuRenderer(renderer, assets, menu_style, content_vp).render(menu)

    # ── Screen transitions ────────────────────────────────────────────

    _menu_stack_depth = 0
    _captured_screen_tex = None

    def _on_screen_pre_close():
        nonlocal _captured_screen_tex
        tex = sdl2.SDL_CreateTexture(
            renderer,
            sdl2.SDL_PIXELFORMAT_RGBA8888,
            sdl2.SDL_TEXTUREACCESS_TARGET,
            cw, ch,
        )
        if tex:
            sdl2.SDL_SetTextureBlendMode(tex, sdl2.SDL_BLENDMODE_BLEND)
            sdl2.SDL_SetRenderTarget(renderer, tex)
            _capture_screen()
            sdl2.SDL_SetRenderTarget(renderer, None)
            _captured_screen_tex = tex

    def _on_screen_close():
        nonlocal _menu_stack_depth, _captured_screen_tex
        if _captured_screen_tex:
            animator.start_pop_with_texture(_captured_screen_tex)
            _captured_screen_tex = None
        else:
            animator.start_pop(_capture_screen)
        while len(menu.stack) > _menu_stack_depth:
            menu.stack.pop()
        animator.capture_new(_capture_menu)
        # Rebuild menu root so "Now Playing" reflects current state
        menu.rebuild_root(build_main_menu(close_menu_fn=lambda: menu.go_to_root()))

    screen_manager = ScreenManager(on_close=_on_screen_close, on_pre_close=_on_screen_pre_close)

    def close_menu_and_open_screen(screen_cls):
        nonlocal _menu_stack_depth
        _menu_stack_depth = len(menu.stack)
        animator.start_push(_capture_menu)
        screen_manager.open(screen_cls)
        if hasattr(screen_manager._screen, 'set_animator'):
            screen_manager._screen.set_animator(animator)
        animator.capture_new(_capture_screen)
        # Rebuild menu root so "Now Playing" appears when returning to menu
        menu.rebuild_root(build_main_menu(close_menu_fn=lambda: menu.go_to_root()))

    # ── Menu navigation callbacks ─────────────────────────────────────

    def _on_menu_push():
        animator.start_push(_capture_menu)

    def _on_menu_push_done():
        animator.capture_new(_capture_menu)

    def _on_menu_pop():
        animator.start_pop(_capture_menu)

    def _on_menu_pop_done():
        animator.capture_new(_capture_menu)

    menu = MenuController(
        build_main_menu(close_menu_fn=lambda: menu.go_to_root()),
        root_title="nuPod",
        on_push=_on_menu_push,
        on_pop=_on_menu_pop,
        on_post_push=_on_menu_push_done,
        on_post_pop=_on_menu_pop_done,
    )

    last = time.perf_counter()
    event = sdl2.SDL_Event()

    while running[0]:
        now = time.perf_counter()
        dt = now - last
        last = now

        # Process input (skip during animation)
        if not animator.active:
            while sdl2.SDL_PollEvent(event):
                if event.type == sdl2.SDL_QUIT:
                    running[0] = False
                    continue

                inp = input_stub.poll(event)
                if inp is None:
                    continue

                # ── Screen is active → delegate to screen ───────────────────
                if screen_manager.active:
                    consumed = screen_manager.handle_input(inp)
                    if isinstance(inp, ButtonPress) and inp.button == Button.UP and not consumed:
                        screen_manager.close()
                    continue

                # ── Menu is active → handle input ────────────────────────────
                if isinstance(inp, ScrollEvent):
                    menu.handle(inp)
                    continue

                if isinstance(inp, ButtonPress):
                    btn = inp.button

                    if btn == Button.CENTER:
                        screen_cls = menu.get_selected_screen_cls()
                        if screen_cls:
                            close_menu_and_open_screen(screen_cls)
                            continue
                        menu.handle(inp)
                        continue

                    if btn == Button.UP:
                        menu.handle(inp)
                        continue

                    if btn == Button.LEFT:
                        menu.handle(inp)
                        continue

                    if btn == Button.DOWN:
                        # DOWN (Play/Pause) only works in the Now Playing screen.
                        # At the menu level, pass through to the menu handler
                        # (does nothing unless in adjust mode).
                        menu.handle(inp)
                        continue

                    if btn == Button.RIGHT:
                        if audio.is_audio_active():
                            audio.set_elapsed_sec(0.0)
                        continue

                    menu.handle(inp)

        # Update all hardware stubs
        battery.tick_stub(dt)
        hwclock.tick_stub(dt)
        disk.tick_stub(dt)
        audio.tick_stub(dt)
        display.tick_stub(dt)
        storage.tick_stub(dt)
        volume.tick_stub(dt)
        settings.tick_stub(dt)
        hwinput.tick_stub(dt)

        # Render
        render()

        sdl2.SDL_RenderPresent(renderer)
        sdl2.SDL_Delay(16)

    sdl2.SDL_DestroyRenderer(renderer)
    sdl2.SDL_DestroyWindow(window)
    sdlttf.TTF_Quit()
    sdlimage.IMG_Quit()
    sdl2.SDL_Quit()


if __name__ == "__main__":
    sys.exit(main())
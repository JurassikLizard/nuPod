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
from engine.menus import build_main_menu

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


def render_status_bar(renderer, assets, theme):
    """Draw the iPod classic status bar: time (center), battery (right),
    playmode/disk (left), hold (left)."""
    sb = theme.get("statusbar", {})
    sb_h = sb.get("height", 22)
    canvas_w = theme["canvas"]["width"]

    text_color = hex_rgb(theme.get("colors", {}).get("statusbar_text", "000000"))

    # Bar background
    bg = hex_rgb(theme.get("colors", {}).get("background", "FFFFFF"))
    sdl2.SDL_SetRenderDrawColor(renderer, *bg, 255)
    sdl2.SDL_RenderFillRect(renderer, sdl2.SDL_Rect(0, 0, canvas_w, sb_h))

    # Bottom border line of status bar
    border_color = hex_rgb(theme.get("colors", {}).get("secondary_text", "CCCCCC"))
    sdl2.SDL_SetRenderDrawColor(renderer, *border_color, 200)
    sdl2.SDL_RenderDrawLine(renderer, 0, sb_h - 1, canvas_w, sb_h - 1)

    # Clock text (center) — uses hardware.clock directly
    t = int(time.time())
    if t % 10 < 5:
        clock_str = hwclock.format_time()
    else:
        clock_str = "Now Playing" if audio.is_audio_active() else "iPod"

    tex, tw, th = assets.render_text(clock_str, text_color)
    if tex:
        tw, th = int(tw), int(th)
        cx = (canvas_w - tw) // 2
        dst = sdl2.SDL_Rect(cx, (sb_h - th) // 2, tw, th)
        sdl2.SDL_RenderCopy(renderer, tex, None, dst)
        sdl2.SDL_DestroyTexture(tex)

    # Battery sprite (right side) — uses hardware.battery directly
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
            dst = sdl2.SDL_Rect(canvas_w - bfw - 2, 4, bfw, bfh)
            sdl2.SDL_RenderCopy(renderer, btex, src, dst)
    except Exception:
        pass

    # Playmode / disk sprite (left side) — uses hardware.disk/audio directly
    try:
        if disk.is_disk_active():
            dtex, dfw, dfh, dframes = assets.get_sprite("disk")
            if dtex:
                frame = int(time.time() * 10) % dframes
                src = sdl2.SDL_Rect(0, frame * dfh, dfw, dfh)
                dst = sdl2.SDL_Rect(3, 2, dfw, dfh)
                sdl2.SDL_RenderCopy(renderer, dtex, src, dst)
        else:
            ptex, pfw, pfh, pframes = assets.get_sprite("playmode")
            if ptex:
                frame = {"PLAYING": 0, "PAUSED": 1, "FF": 2, "REW": 3}.get(audio.get_play_state(), 0)
                src = sdl2.SDL_Rect(0, frame * pfh, pfw, pfh)
                dst = sdl2.SDL_Rect(4, 5, pfw, pfh)
                sdl2.SDL_RenderCopy(renderer, ptex, src, dst)
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
    menu_style = {
        "row_height": 18,
        "text_color": hex_rgb(colors["foreground"]),
        "background_color": hex_rgb(colors["background"]),
        "selector_start": hex_rgb(colors["selector_start"]),
        "selector_end": hex_rgb(colors["selector_end"]),
        "selector_text_color": hex_rgb(colors["selector_text"]),
        "secondary_text_color": hex_rgb(colors.get("secondary_text", "999999")),
    }
    vp = theme["menu_viewport"]
    vp_tuple = (vp["x"], vp["y"], vp["w"], vp["h"])

    input_stub = KeyboardInputStub()

    running = [True]

    # Screen manager handles full-screen leaf views
    screen_manager = ScreenManager()

    def close_menu_and_open_screen(screen_cls):
        """Go to root menu and push a screen."""
        menu.go_to_root()
        screen_manager.open(screen_cls)

    menu = MenuController(
        build_main_menu(close_menu_fn=lambda: menu.go_to_root()),
        root_title="Main Menu",
    )

    bg_rgb = hex_rgb(colors["background"])
    last = time.perf_counter()
    event = sdl2.SDL_Event()

    while running[0]:
        now = time.perf_counter()
        dt = now - last
        last = now

        # Process input
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
                # UP (Menu) button closes the screen if not consumed by the screen
                if isinstance(inp, ButtonPress) and inp.button == Button.UP and not consumed:
                    screen_manager.close()
                continue

            # ── Menu is active → handle input ────────────────────────────
            if isinstance(inp, ScrollEvent):
                menu.handle(inp)
                continue

            if isinstance(inp, ButtonPress):
                btn = inp.button

                # CENTER on a "screen" item → open full-screen view
                if btn == Button.CENTER:
                    screen_cls = menu.get_selected_screen_cls()
                    if screen_cls:
                        close_menu_and_open_screen(screen_cls)
                        continue
                    menu.handle(inp)
                    continue

                # UP (Menu) button → menu handles (short=back one, long=root)
                if btn == Button.UP:
                    menu.handle(inp)
                    continue

                # LEFT (Rewind / adjust left) → menu handles in adjust mode
                if btn == Button.LEFT:
                    menu.handle(inp)
                    continue

                # DOWN (Play/Pause) button → toggle playback
                if btn == Button.DOWN:
                    ps = audio.get_play_state()
                    if ps == "PLAYING":
                        audio.set_play_state("PAUSED")
                    elif ps == "PAUSED":
                        audio.set_play_state("PLAYING")
                    else:
                        audio.set_play_state("PLAYING")
                    continue

                # RIGHT (Forward) button → skip track
                if btn == Button.RIGHT:
                    if audio.is_audio_active():
                        audio.set_elapsed_sec(0.0)
                    continue

                # Everything else → menu
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
        sdl2.SDL_SetRenderDrawColor(renderer, *bg_rgb, 255)
        sdl2.SDL_RenderClear(renderer)

        if screen_manager.active:
            # Full-screen view (no menu)
            screen_manager.render(renderer, assets, theme, (0, 0, cw, ch))
        else:
            # Status bar always visible when menu is showing
            render_status_bar(renderer, assets, theme)
            # Menu overlay in viewport
            menu_renderer = MenuRenderer(renderer, assets, menu_style, vp_tuple)
            menu_renderer.render(menu)

        sdl2.SDL_RenderPresent(renderer)
        sdl2.SDL_Delay(16)

    sdl2.SDL_DestroyRenderer(renderer)
    sdl2.SDL_DestroyWindow(window)
    sdlttf.TTF_Quit()
    sdlimage.IMG_Quit()
    sdl2.SDL_Quit()


if __name__ == "__main__":
    sys.exit(main())
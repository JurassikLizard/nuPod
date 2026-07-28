"""
iPod-accurate input model.

The iPod Clickwheel has 5 physical buttons + a touch-sensitive scroll wheel:

  Buttons (the 4 cardinal points + center click):
    CENTER — Select / confirm (center of the wheel)
    UP    — Menu / back (top segment of the wheel)
    DOWN  — Play/Pause (bottom segment)
    LEFT  — Rewind / adjust left (left segment)
    RIGHT — Forward / adjust right (right segment)

  Scroll wheel:
    CW  (clockwise)        → scroll down / next
    CCW (counter-clockwise) → scroll up / previous

  Keyboard mapping:
    Enter          → CENTER
    Arrow Up       → UP (Menu / back button)
    Arrow Down     → DOWN (Play/Pause button)
    Arrow Left     → LEFT (Rewind / adjust left)
    Arrow Right    → RIGHT (Forward / adjust right)
    Mouse scroll   → Scroll (direction follows wheel)

  UP (Menu) button behavior:
    Short press (< 3s hold, release) = back one level
    Long press  (≥ 3s hold, release) = go to main menu
    Fires on KEYUP so duration can be measured.

  DOWN (Play/Pause) button behavior:
    Short press = toggle play/pause (fires on KEYDOWN for responsiveness)
    Long press  (≥ 3s hold, release) = stop playback (fires on KEYUP)
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional
import time

import sdl2


# ── button enumeration ──────────────────────────────────────────────────────

class Button(Enum):
    CENTER = auto()
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()


# ── event types ─────────────────────────────────────────────────────────────

@dataclass
class ButtonPress:
    """A physical button press event."""
    button: Button
    long_press: bool = False
    held_duration: float = 0.0


@dataclass
class ScrollEvent:
    """Scroll wheel movement.

    ``direction`` follows the screen convention:
        -1   = CCW  → scroll up / previous
        +1   = CW   → scroll down / next
    """
    direction: int
    clicks: int = 1


# Unified input type that the rest of the app consumes
InputEvent = ButtonPress | ScrollEvent


# ── keyboard / mouse mapping ────────────────────────────────────────────────

_KEY_TO_BUTTON = {
    sdl2.SDLK_RETURN: Button.CENTER,
    sdl2.SDLK_UP:     Button.UP,
    sdl2.SDLK_DOWN:   Button.DOWN,
    sdl2.SDLK_LEFT:   Button.LEFT,
    sdl2.SDLK_RIGHT:  Button.RIGHT,
}

_LONG_PRESS_THRESHOLD_S = 3.0
_LONG_PRESS_BUTTONS = {Button.UP, Button.DOWN}

# Buttons that fire only on KEYUP (for proper long-press measurement).
# All others fire on KEYDOWN (responsive). Buttons in this set that are
# ALSO in _LONG_PRESS_BUTTONS fire on KEYDOWN (responsive short press)
# plus KEYUP (long press only).
_KEYUP_ONLY = {Button.UP}


# ── input stub ──────────────────────────────────────────────────────────────

class KeyboardInputStub:
    """Translates SDL events into abstract ButtonPress / ScrollEvent values.

    Tracks key-down timestamps so that the UP (Menu) button can distinguish
    between a short tap (back one level) and a long hold (go to root).
    """

    def __init__(self):
        self._held_keys: dict[int, float] = {}  # sdl_key_sym → press_time

    def poll(self, sdl_event) -> Optional[InputEvent]:
        """Translate one SDL event into an InputEvent, or None."""

        # ── key down ────────────────────────────────────────────────────
        if sdl_event.type == sdl2.SDL_KEYDOWN:
            sym = sdl_event.key.keysym.sym
            if sym in _KEY_TO_BUTTON:
                button = _KEY_TO_BUTTON[sym]
                self._held_keys[sym] = time.time()
                # _KEYUP_ONLY buttons (UP/Menu) fire only on KEYUP so we
                # can measure hold duration.  All other buttons fire
                # immediately on KEYDOWN for responsive feel.
                if button not in _KEYUP_ONLY:
                    return ButtonPress(button=button)
            return None

        # ── key up ──────────────────────────────────────────────────────
        if sdl_event.type == sdl2.SDL_KEYUP:
            sym = sdl_event.key.keysym.sym
            if sym in _KEY_TO_BUTTON:
                button = _KEY_TO_BUTTON[sym]
                pressed_time = self._held_keys.pop(sym, None)
                if pressed_time is not None:
                    duration = time.time() - pressed_time
                    if button in _LONG_PRESS_BUTTONS and duration >= _LONG_PRESS_THRESHOLD_S:
                        # Long press detected for any long-press-capable button
                        return ButtonPress(
                            button=button,
                            long_press=True,
                            held_duration=duration,
                        )
                    if button in _KEYUP_ONLY:
                        # UP short press fires here (KEYUP)
                        return ButtonPress(button=button, long_press=False, held_duration=duration)
                    # OTHER short press was already handled on KEYDOWN; nothing extra
            return None

        # ── mouse wheel → scroll ────────────────────────────────────────
        if sdl_event.type == sdl2.SDL_MOUSEWHEEL:
            # SDL: y > 0 = scroll up (natural) = CCW = move up in list
            #      y < 0 = scroll down = CW = move down in list
            direction = -1 if sdl_event.wheel.y > 0 else 1
            return ScrollEvent(direction=direction)

        return None
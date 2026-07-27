"""ScreenManager: owns the current full-screen leaf view.

The main loop checks ScreenManager.active first:
- If active, input goes to the screen, rendering draws the screen.
- When the screen returns "back", the ScreenManager pops it and the
  menu becomes visible again.
"""

from typing import Optional, Type
from .input import InputEvent
from .screens import Screen


class ScreenManager:
    """Manages a single active screen (not a stack — only one at a time)."""

    def __init__(self):
        self._screen: Optional[Screen] = None
        self._screen_cls: Optional[Type] = None

    @property
    def active(self) -> bool:
        return self._screen is not None

    @property
    def screen_cls(self):
        return self._screen_cls

    def open(self, screen_cls: Type, state):
        """Instantiate a screen class and set it as active."""
        self._screen = screen_cls()
        self._screen_cls = screen_cls
        self._screen.on_enter(state)

    def close(self, state):
        """Close the active screen and return to menu."""
        if self._screen:
            self._screen.on_exit(state)
            self._screen = None
            self._screen_cls = None

    def handle_input(self, event: InputEvent, state) -> bool:
        """Delegate input to the active screen. Returns True if consumed."""
        if not self._screen:
            return False
        result = self._screen.handle_input(event, state)
        if result == "back":
            self.close(state)
            return True
        return True

    def render(self, renderer, assets, state, theme, viewport):
        """Delegate rendering to the active screen."""
        if self._screen:
            self._screen.render(renderer, assets, state, theme, viewport)
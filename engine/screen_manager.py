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

    def __init__(self, on_close=None, on_pre_close=None):
        self._screen: Optional[Screen] = None
        self._screen_cls: Optional[Type] = None
        self._on_close = on_close
        self._on_pre_close = on_pre_close

    @property
    def active(self) -> bool:
        return self._screen is not None

    @property
    def title(self) -> str:
        """Title of the active screen, shown in the status bar."""
        return self._screen.title if self._screen else ""

    @property
    def screen_cls(self):
        return self._screen_cls

    def open(self, screen_cls: Type):
        """Instantiate a screen class and set it as active."""
        self._screen = screen_cls()
        self._screen_cls = screen_cls
        self._screen.on_enter()

    def close(self):
        """Close the active screen and return to menu."""
        if self._screen:
            self._screen.on_exit()
            # Pre-close callback fires before the screen is destroyed,
            # so the animation system can capture the last frame.
            if self._on_pre_close:
                self._on_pre_close()
            self._screen = None
            self._screen_cls = None
            if self._on_close:
                self._on_close()

    def handle_input(self, event: InputEvent) -> bool:
        """Delegate input to the active screen. Returns True if consumed."""
        if not self._screen:
            return False
        result = self._screen.handle_input(event)
        if result == "back":
            self.close()
            return True
        return True

    def render(self, renderer, assets, theme, viewport, dt=0.0):
        """Delegate rendering to the active screen."""
        if self._screen:
            self._screen.render(renderer, assets, theme, viewport, dt)
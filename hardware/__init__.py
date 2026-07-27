"""
Hardware interface for the iPod Classic emulator.

Each hardware subsystem is a module with:
- Public getter/setter functions (``get_xxx()`` / ``set_xxx()``)
- A ``tick_stub(dt)`` function for simulation
- Module-level private stub state that can be replaced with real hardware

Usage (stub mode):
    import hardware.battery as battery
    pct = battery.get_battery_percent()
    battery.tick_stub(dt)

Real hardware swap:
    # Replace the module entirely with a real driver that exports
    # the same public functions.
"""
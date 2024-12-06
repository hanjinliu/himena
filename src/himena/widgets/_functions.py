from __future__ import annotations

from himena.widgets import current_instance
from contextlib import suppress


def set_status_tip(text: str, duration: float = 10) -> None:
    """Set a status tip to the current main window for duration (second)."""

    with suppress(Exception):
        ins = current_instance()
        ins.set_status_tip(text, duration=duration)
    return None

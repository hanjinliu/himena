from __future__ import annotations
from pathlib import Path
from typing import Any, Literal, overload

from himena.types import ClipboardDataModel
from himena.widgets import current_instance
from contextlib import suppress


def set_status_tip(text: str, duration: float = 10.0) -> None:
    """Set a status tip to the current main window for duration (second).

    This method can be safely called from any thread.

    Parameters
    ----------
    text : str
        Text to show in the status bar.
    duration : float, default 10.0
        Duration (seconds) to show the status tip.
    """

    with suppress(Exception):
        ins = current_instance()
        ins.set_status_tip(text, duration=duration)


def get_clipboard() -> ClipboardDataModel:
    """Get the current clipboard data."""
    return current_instance().clipboard


@overload
def set_clipboard(
    *,
    text: str | None = None,
    html: str | None = None,
    image: Any | None = None,
    files: list[str | Path] | None = None,
    interanal_data: Any | None = None,
) -> None: ...


@overload
def set_clipboard(model: ClipboardDataModel, /) -> None: ...


def set_clipboard(model=None, **kwargs) -> None:
    """Set data to clipboard."""
    ins = current_instance()
    if model is not None:
        if kwargs:
            raise TypeError("Cannot specify both model and keyword arguments")
        ins.clipboard = model
    else:
        ins.set_clipboard(**kwargs)
    return None


def notify(text: str, duration: float = 5.0) -> None:
    """Show a notification popup in the bottom right corner.

    Parameters
    ----------
    text : str
        Text to show in the notification.
    duration : float, default 5.0
        Duration (seconds) to show the notification.
    """
    ins = current_instance()
    ins.show_notification(text, duration)


def show_tooltip(
    text: str,
    duration: float = 3.0,
    behavior: Literal["stay", "follow", "until_move"] = "follow",
) -> None:
    """Show a tooltip next to the cursor for a duration (sec).

    Parameters
    ----------
    text : str
        HTML text to show in the tooltip.
    duration : float, default 3.0
        Duration (seconds) to show the tooltip.
    behavior : str, default "follow"
        Behavior of the tooltip. "stay" to show at the position where it is created,
        "follow" to follow the cursor, "until_move" to show until the cursor moves.
    """
    with suppress(Exception):
        ins = current_instance()
        ins.show_tooltip(text, duration=duration, behavior=behavior)


def append_result(item: dict[str, Any], /) -> None:
    """Append a new result to the result stack."""
    ins = current_instance()
    ins._backend_main_window._append_result(item)

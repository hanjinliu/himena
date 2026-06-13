from __future__ import annotations

from typing import Any, Callable, Iterator

from himena.widgets import MainWindow
from contextlib import contextmanager


@contextmanager
def notification_response(ui: MainWindow, choice: str) -> Iterator[None]:
    """Simulate clicking a button in a notification dialog in this context.

    >>> with notification_response(ui, "Close"):
    ...     ui.show_notification("This is a notification", callbacks={"Close": func})
    """
    old_inst = ui._instructions
    try:
        ui._instructions = ui._instructions.updated(notification_response=choice)
        yield
    finally:
        ui._instructions = old_inst


@contextmanager
def notification_callback(
    ui: MainWindow, callback: Callable[[str, str], Any]
) -> Iterator[None]:
    """Set a callback to be called when a notification is shown in this context.

    The callback will be called with the text and title of the notification.
    """
    if not callable(callback):
        raise ValueError("callback must be callable")
    old_inst = ui._instructions
    try:
        ui._instructions = ui._instructions.updated(notification_callback=callback)
        yield
    finally:
        ui._instructions = old_inst

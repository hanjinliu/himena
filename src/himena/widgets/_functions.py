from __future__ import annotations
from pathlib import Path
from typing import Any, overload

from himena.types import ClipboardDataModel
from himena.widgets import current_instance
from contextlib import suppress


def set_status_tip(text: str, duration: float = 10.0) -> None:
    """Set a status tip to the current main window for duration (second)."""

    with suppress(Exception):
        ins = current_instance()
        ins.set_status_tip(text, duration=duration)
    return None


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
    """Show a notification popup in the bottom right corner."""
    ins = current_instance()
    ins._backend_main_window._show_notification(text, duration)
    return None


def append_result(item: dict[str, Any], /) -> None:
    """Append a new result to the result stack."""
    ins = current_instance()
    ins._backend_main_window._append_result(item)
    return None


# def subprocess_run(command_args, /, *args, blocking: bool = True, **kwargs):
#     """Run a subprocess command."""
#     import subprocess

#     if isinstance(command_args, str):
#         command_args_normed = command_args
#     else:
#         # first check all the types
#         for arg in command_args:
#             if not isinstance(arg, (str, WidgetDataModel)):
#                 raise TypeError(f"Invalid argument type: {type(arg)}")
#         command_args_normed = []
#         for arg in command_args:
#             if isinstance(arg, str):
#                 command_args_normed.append(arg)
#             elif isinstance(arg, WidgetDataModel):
#                 arg.write_to_directory(...)
#                 command_args_normed.append(...)
#             else:
#                 raise RuntimeError("Unreachable code")
#     if blocking:
#         return subprocess.run(command_args_normed, *args, **kwargs)
#     else:
#         return subprocess.Popen(command_args_normed, *args, **kwargs)

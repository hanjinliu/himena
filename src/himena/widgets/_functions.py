from __future__ import annotations

from himena.widgets import current_instance
from contextlib import suppress


def set_status_tip(text: str, duration: float = 10.0) -> None:
    """Set a status tip to the current main window for duration (second)."""

    with suppress(Exception):
        ins = current_instance()
        ins.set_status_tip(text, duration=duration)
    return None


def notify(text: str, duration: float = 5.0) -> None:
    """Show a notification popup in the bottom right corner."""
    ins = current_instance()
    ins._backend_main_window._show_notification(text, duration)
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

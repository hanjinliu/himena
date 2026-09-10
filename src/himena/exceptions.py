from __future__ import annotations

from contextlib import suppress
import sys
from typing import Any, Callable, TYPE_CHECKING
import warnings
import threading

if TYPE_CHECKING:
    from types import TracebackType


class Cancelled(Exception):
    """Exception raised when the user cancels the operation."""


class DeadSubwindowError(RuntimeError):
    """Exception raised when a subwindow is not alive in the main window."""


class NotExecutable(RuntimeError):
    """Exception raised when the workflow cannot be executed."""


_SYS_EXCEPTHOOK = sys.excepthook
_SHOW_WARNING = warnings.showwarning
_THREAD_EXCEPTHOOK = threading.excepthook


class ExceptionHandler:
    """Handle exceptions in the GUI thread."""

    def __init__(
        self,
        hook: Callable[[type[Exception], Exception, TracebackType], Any],
        warning_hook: Callable[[warnings.WarningMessage], Any] = None,
    ):
        self._except_hook = hook
        self._warning_hook = warning_hook

    def __enter__(self):
        sys.excepthook = self._except_hook
        threading.excepthook = self._except_hook
        if self._warning_hook is not None:
            warnings.showwarning = self.show_warning
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        sys.excepthook = _SYS_EXCEPTHOOK
        threading.excepthook = _THREAD_EXCEPTHOOK
        if self._warning_hook is not None:
            warnings.showwarning = _SHOW_WARNING

    def show_warning(self, message, category, filename, lineno, file=None, line=None):
        """Handle warnings."""
        msg = warnings.WarningMessage(message, category, filename, lineno, file, line)
        self._warning_hook(msg)


def default_show_warning(warning: warnings.WarningMessage) -> None:
    """Show a warning using the default `warnings.showwarning` (usually stderr)."""
    with suppress(Exception):
        _SHOW_WARNING(
            warning.message,
            warning.category,
            warning.filename,
            warning.lineno,
            warning.file,
            warning.line,
        )

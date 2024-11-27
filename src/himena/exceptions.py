from __future__ import annotations

import sys
from typing import Any, Callable, TYPE_CHECKING
import warnings

if TYPE_CHECKING:
    from types import TracebackType


class Cancelled(Exception):
    """Exception raised when the user cancels the operation."""


class DeadSubwindowError(RuntimeError):
    """Exception raised when a subwindow is not alive in the main window."""


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
        self._original_excepthook = sys.excepthook
        sys.excepthook = self._except_hook
        self._original_warning = warnings.showwarning
        if self._warning_hook is not None:
            warnings.showwarning = self.show_warning
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        sys.excepthook = self._original_excepthook
        if self._warning_hook is not None:
            warnings.showwarning = self._original_warning
        return None

    def show_warning(self, message, category, filename, lineno, file=None, line=None):
        """Handle warnings."""
        msg = warnings.WarningMessage(message, category, filename, lineno, file, line)
        self._warning_hook(msg)
        return None

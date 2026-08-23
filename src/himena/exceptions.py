from __future__ import annotations

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


__SYS_EXCEPTHOOK = sys.excepthook
__SHOW_WARNING = warnings.showwarning
__THREAD_EXCEPTHOOK = threading.excepthook


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
        sys.excepthook = __SYS_EXCEPTHOOK
        threading.excepthook = __THREAD_EXCEPTHOOK
        if self._warning_hook is not None:
            warnings.showwarning = __SHOW_WARNING

    def show_warning(self, message, category, filename, lineno, file=None, line=None):
        """Handle warnings."""
        msg = warnings.WarningMessage(message, category, filename, lineno, file, line)
        self._warning_hook(msg)

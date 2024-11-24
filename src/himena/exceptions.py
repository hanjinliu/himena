class Cancelled(Exception):
    """Exception raised when the user cancels the operation."""


class DeadSubwindowError(RuntimeError):
    """Exception raised when a subwindow is not alive in the main window."""

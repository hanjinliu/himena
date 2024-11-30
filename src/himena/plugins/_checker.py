from __future__ import annotations

from typing import TypeVar

_T = TypeVar("_T")

_ALLOWED_METHODS = frozenset(
    [
        "update_model",
        "to_model",
        "model_type",
        "control_widget",
        "is_modified",
        "set_modified",
        "size_hint",
        "is_editable",
        "set_editable",
        "merge_model",
        "mergeable_model_types",
        "display_name",
        "theme_changed_callback",
        "window_activated_callback",
        "window_closed_callback",
        "window_resized_callback",
    ]
)


def protocol_override(f: _T) -> _T:
    """Check if the method is allowed as a himena-aware protocol."""
    if f.__name__ not in _ALLOWED_METHODS:
        raise ValueError(f"Method {f} is not a allowed protocol.")
    return f


def call_window_closed_callback(win):
    return _call_callback(win, "window_closed_callback")


def call_window_activated_callback(win):
    return _call_callback(win, "window_activated_callback")


def call_theme_changed_callback(win, theme):
    return _call_callback(win, "theme_changed_callback", theme)


def call_window_resized_callback(win, size: tuple[int, int]):
    return _call_callback(win, "window_resized_callback", size)


def _call_callback(win, callback_name: str, *args):
    if cb := getattr(win, callback_name, None):
        if callable(cb):
            cb(*args)
            return
        raise TypeError("`window_activated_callback` must be a callable")

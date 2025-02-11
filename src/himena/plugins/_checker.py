from __future__ import annotations

from typing import TypeVar

from himena.types import Size

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
        "dropped_callback",
        "allowed_drop_types",
        "theme_changed_callback",
        "widget_activated_callback",
        "widget_closed_callback",
        "widget_resized_callback",
        "widget_added_callback",
        "get_user_context",
        "default_title",
        "native_widget",
        "update_value",
        "update_configs",
    ]
)


def validate_protocol(f: _T) -> _T:
    """Check if the method is allowed as a himena protocol."""
    if f.__name__ not in _ALLOWED_METHODS:
        raise ValueError(f"Method {f} is not an allowed protocol name.")
    return f


def call_widget_closed_callback(win):
    return _call_callback(win, "widget_closed_callback")


def call_widget_activated_callback(win):
    return _call_callback(win, "widget_activated_callback")


def call_theme_changed_callback(win, theme):
    return _call_callback(win, "theme_changed_callback", theme)


def call_widget_resized_callback(win, size_old: Size, size_new: Size):
    return _call_callback(win, "widget_resized_callback", size_old, size_new)


def call_widget_added_callback(win):
    return _call_callback(win, "widget_added_callback")


def _call_callback(win, callback_name: str, *args):
    if cb := getattr(win, callback_name, None):
        if callable(cb):
            cb(*args)
            return
        raise TypeError(f"`{callback_name}` must be a callable")

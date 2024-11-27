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
        "theme_changed_callback",
        "merge_model",
        "mergeable_model_types",
        "display_name",
    ]
)


def protocol_override(f: _T) -> _T:
    """Check if the method is allowed as a himena-aware protocol."""
    if f.__name__ not in _ALLOWED_METHODS:
        raise ValueError(f"Method {f} is not a allowed protocol.")
    return f

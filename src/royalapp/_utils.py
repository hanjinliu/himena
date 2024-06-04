from __future__ import annotations
import sys
from typing import Callable, Any
from types import TracebackType
from royalapp.types import WidgetDataModel


def get_widget_data_model_variable(func: Callable) -> type | None:
    annots = [v for k, v in func.__annotations__.items() if k != "return"]
    if len(annots) != 1:
        return None
    annot = annots[0]
    if not (hasattr(annot, "__origin__") and hasattr(annot, "__args__")):
        return None
    if annot.__origin__ is not WidgetDataModel:
        return None
    if len(annot.__args__) != 1:
        return None
    return annot.__args__[0]


def has_widget_data_model_argument(func: Callable) -> bool:
    """If true, the function has a WidgetDataModel type hint."""
    for k, v in func.__annotations__.items():
        if k == "return":
            continue
        if v is WidgetDataModel:
            return True
        if hasattr(v, "__origin__") and hasattr(v, "__args__"):
            if v.__origin__ is WidgetDataModel:
                return True
    return False


class ExceptionHandler:
    """Handle exceptions in the GUI thread."""

    def __init__(
        self, hook: Callable[[type[Exception], Exception, TracebackType], Any]
    ):
        self._excepthook = hook

    def __enter__(self):
        self._original_excepthook = sys.excepthook
        sys.excepthook = self._excepthook
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        sys.excepthook = self._original_excepthook
        return None

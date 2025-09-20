__version__ = "0.0.14"
__author__ = "Hanjin Liu"

from himena.core import (
    new_window,
    create_model,
    create_array_model,
    create_dataframe_model,
    create_image_model,
    create_table_model,
    create_text_model,
)
from himena.consts import StandardType
from himena.widgets import MainWindow
from himena.types import WidgetDataModel, ClipboardDataModel, Parametric
from himena._app_model import AppContext

__all__ = [
    "new_window",
    "create_model",
    "create_array_model",
    "create_dataframe_model",
    "create_image_model",
    "create_table_model",
    "create_text_model",
    "StandardType",
    "MainWindow",
    "WidgetDataModel",
    "ClipboardDataModel",
    "Parametric",
    "AppContext",
]


def __getattr__(name: str):
    if name == "plotting":
        # This is a shortcut, not deprecated
        from himena.standards import plotting

        return plotting
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

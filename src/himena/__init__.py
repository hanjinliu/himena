__version__ = "0.0.14"
__author__ = "Hanjin Liu"

from typing import TYPE_CHECKING
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

if TYPE_CHECKING:
    from himena.standards import plotting  # noqa: F401


def __getattr__(name: str):
    if name == "plotting":
        from himena.standards import plotting

        return plotting
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

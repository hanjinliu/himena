from magicgui.type_map import TypeMap
from himena.qt._magicgui._basic_widgets import (
    IntEdit,
    FloatEdit,
    IntListEdit,
    FloatListEdit,
)
from himena.qt._magicgui._modeldrop import ModelDrop
from himena.qt._magicgui._toggle_switch import ToggleSwitch
from himena.qt._magicgui._color import ColorEdit, ColormapEdit
from himena.types import WidgetDataModel
from cmap import Color, Colormap

TYPE_MAP = TypeMap()


def register_magicgui_types():
    """Register magicgui types."""

    TYPE_MAP.register_type(WidgetDataModel, widget_type=ModelDrop)
    TYPE_MAP.register_type(bool, widget_type=ToggleSwitch)
    TYPE_MAP.register_type(int, widget_type=IntEdit)
    TYPE_MAP.register_type(float, widget_type=FloatEdit)
    TYPE_MAP.register_type(list[int], widget_type=IntListEdit)
    TYPE_MAP.register_type(list[float], widget_type=FloatListEdit)
    TYPE_MAP.register_type(Color, widget_type=ColorEdit)
    TYPE_MAP.register_type(Colormap, widget_type=ColormapEdit)


def get_type_map():
    """Get the magicgui type map for himena."""
    return TYPE_MAP

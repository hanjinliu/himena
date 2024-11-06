from magicgui import register_type
from royalapp.qt._magicgui._basic_widgets import IntEdit, FloatEdit
from royalapp.qt._magicgui._modeldrop import ModelDrop
from royalapp.qt._magicgui._toggle_switch import ToggleSwitch
from royalapp.types import WidgetDataModel


def register_magicgui_types():
    """Register magicgui types."""
    register_type(WidgetDataModel, widget_type=ModelDrop)
    register_type(int, widget_type=IntEdit)
    register_type(float, widget_type=FloatEdit)
    register_type(bool, widget_type=ToggleSwitch)

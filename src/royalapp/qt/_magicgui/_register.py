from magicgui import register_type
from royalapp.qt._magicgui._basicwidget import IntEdit, FloatEdit
from royalapp.qt._magicgui._modeldrop import ModelDrop
from royalapp.types import WidgetDataModel


def register_magicgui_types():
    register_type(WidgetDataModel, widget_type=ModelDrop)
    register_type(int, widget_type=IntEdit)
    register_type(float, widget_type=FloatEdit)

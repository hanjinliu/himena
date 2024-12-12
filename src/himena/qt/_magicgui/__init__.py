from himena.qt._magicgui._register import register_magicgui_types, get_type_map
from himena.qt._magicgui._color import ColorEdit, ColormapEdit
from himena.qt._magicgui._face_edge import FacePropertyEdit, EdgePropertyEdit
from himena.qt._magicgui._toggle_switch import ToggleSwitch
from himena.qt._magicgui._basic_widgets import IntEdit, FloatEdit
from himena.qt._magicgui._selection import SelectionEdit
from himena.qt._magicgui._modeldrop import ModelDrop
from himena.qt._magicgui._dtypeedit import NumericDTypeEdit
from himena.qt._magicgui._value_getter import SliderRangeGetter

__all__ = [
    "get_type_map",
    "register_magicgui_types",
    "ColorEdit",
    "ColormapEdit",
    "ToggleSwitch",
    "FacePropertyEdit",
    "EdgePropertyEdit",
    "IntEdit",
    "FloatEdit",
    "ModelDrop",
    "NumericDTypeEdit",
    "SelectionEdit",
    "NumericDTypeEdit",
    "SliderRangeGetter",
]

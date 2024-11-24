from himena.qt._magicgui._register import register_magicgui_types, get_type_map
from himena.qt._magicgui._toggle_switch import ToggleSwitch
from himena.qt._magicgui._basic_widgets import IntEdit, FloatEdit
from himena.qt._magicgui._selection import SelectionEdit
from himena.qt._magicgui._modeldrop import ModelDrop
from himena.qt._magicgui._dtypeedit import NumericDTypeEdit

__all__ = [
    "get_type_map",
    "register_magicgui_types",
    "ToggleSwitch",
    "IntEdit",
    "FloatEdit",
    "ModelDrop",
    "SelectionEdit",
    "NumericDTypeEdit",
]

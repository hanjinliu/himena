from himena.qt.magicgui._register import register_magicgui_types, get_type_map
from himena.qt.magicgui._color import ColorEdit, ColormapEdit
from himena.qt.magicgui._plot_elements import (
    FacePropertyEdit,
    EdgePropertyEdit,
    AxisPropertyEdit,
    DictEdit,
)
from himena.qt.magicgui._toggle_switch import ToggleSwitch
from himena.qt.magicgui._basic_widgets import (
    IntEdit,
    FloatEdit,
    IntListEdit,
    FloatListEdit,
)
from himena.qt.magicgui._file_edit import FileEdit
from himena.qt.magicgui._selection import SelectionEdit
from himena.qt.magicgui._modeldrop import (
    ModelDrop,
    ModelListDrop,
    SubWindowDrop,
    SubWindowListDrop,
)
from himena.qt.magicgui._dtypeedit import NumericDTypeEdit
from himena.qt.magicgui._value_getter import SliderRangeGetter

__all__ = [
    "get_type_map",
    "register_magicgui_types",
    "ColorEdit",
    "ColormapEdit",
    "ToggleSwitch",
    "FacePropertyEdit",
    "EdgePropertyEdit",
    "FileEdit",
    "AxisPropertyEdit",
    "IntEdit",
    "FloatEdit",
    "IntListEdit",
    "FloatListEdit",
    "DictEdit",
    "ModelDrop",
    "ModelListDrop",
    "SubWindowDrop",
    "SubWindowListDrop",
    "NumericDTypeEdit",
    "SelectionEdit",
    "NumericDTypeEdit",
    "SliderRangeGetter",
]

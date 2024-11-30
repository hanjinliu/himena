from __future__ import annotations
from typing import Any, TYPE_CHECKING

from magicgui.types import Undefined
from magicgui.widgets import LineEdit, ComboBox
from magicgui.widgets.bases import ValuedContainerWidget
from cmap import Color, Colormap
from himena.qt._magicgui._color import ColorEdit, ColormapEdit
from himena.qt._magicgui._basic_widgets import FloatEdit
from himena.qt._magicgui._toggle_switch import ToggleSwitch
from himena.consts import MonospaceFontFamily

if TYPE_CHECKING:
    from typing import TypedDict, NotRequired

    class FacePropertyDict(TypedDict):
        color: NotRequired[Color | Colormap]
        hatch: NotRequired[str]

    class EdgePropertyDict(TypedDict):
        color: NotRequired[Color | Colormap]
        width: NotRequired[float]
        style: NotRequired[str]


class ColorOrColorCycleEdit(ValuedContainerWidget):
    def __init__(self, value=Undefined, **kwargs):
        self._use_color_cycle = ToggleSwitch(value=False, text="use color cycle")
        self._color = ColorEdit(value="black")
        self._color_cycle = ColormapEdit(value="tab10", visible=False)
        super().__init__(
            value,
            widgets=[self._use_color_cycle, self._color, self._color_cycle],
            **kwargs,
        )
        self.margins = (0, 0, 0, 0)
        self.min_height = 60
        self._use_color_cycle.changed.connect(self._update_visibility)

    def _update_visibility(self, v: bool):
        self._color_cycle.visible = v
        self._color.visible = not v

    def get_value(self) -> Any:
        return (
            self._color_cycle.value
            if self._use_color_cycle.value
            else self._color.value.hex
        )

    def set_value(self, value: Any):
        try:
            value = Colormap(value)
        except Exception:
            value = Color(value)
            is_cycle = False
        else:
            is_cycle = True

        self._use_color_cycle.value = is_cycle
        if is_cycle:
            self._color_cycle.value = value
        else:
            self._color.value = value


class FacePropertyEdit(ValuedContainerWidget["FacePropertyDict"]):
    def __init__(self, value=Undefined, **kwargs):
        if value is None:
            value = Undefined
        self._face_color = ColorOrColorCycleEdit(value="#FFFFFF", label="color")
        self._face_hatch = LineEdit(value="", label="hatch")
        super().__init__(
            value,
            widgets=[self._face_color, self._face_hatch],
            **kwargs,
        )
        self._face_color.changed.connect(self._emit_value_changed)
        self._face_hatch.changed.connect(self._emit_value_changed)
        self.margins = (0, 0, 0, 0)

    def _emit_value_changed(self):
        self.changed.emit(self.get_value())

    def get_value(self) -> FacePropertyDict:
        return {
            "color": self._face_color.value,
            "hatch": self._face_hatch.value,
        }

    def set_value(self, value: FacePropertyDict):
        value = value or {}
        self._face_color.value = value.get("color", "white")
        self._face_hatch.value = value.get("hatch", "")


class EdgePropertyEdit(ValuedContainerWidget["EdgePropertyDict"]):
    _STYLE_CHOICES = [
        ("———————", "-"),
        ("— — — —", "--"),
        ("-·-·-·-", "-."),
        ("-··-··-", "-.."),
        ("·······", ":"),
    ]

    def __init__(self, value=Undefined, **kwargs):
        if value is None:
            value = Undefined
        self._edge_color = ColorOrColorCycleEdit(value="#000000", label="color")
        self._edge_width = FloatEdit(value=1.0, label="width", min=0.0)
        self._edge_style = ComboBox(
            value="-", choices=self._STYLE_CHOICES, label="style"
        )
        self._edge_style.native.setStyleSheet(f"font-family: {MonospaceFontFamily}")
        super().__init__(
            value,
            widgets=[self._edge_color, self._edge_width, self._edge_style],
            **kwargs,
        )
        self._edge_color.changed.connect(self._emit_value_changed)
        self._edge_width.changed.connect(self._emit_value_changed)
        self._edge_style.changed.connect(self._emit_value_changed)
        self.changed.connect(self._on_property_changed)
        self._on_property_changed(self.get_value())

    def get_value(self) -> EdgePropertyDict:
        return {
            "color": self._edge_color.value,
            "width": round(self._edge_width.value, 2),
            "style": self._edge_style.value,
        }

    def set_value(self, value: EdgePropertyDict):
        value = value or {}
        with self.changed.blocked():
            self._edge_color.value = value.get("color", "black")
            self._edge_width.value = round(value.get("width", 0.0), 2)
            self._edge_style.value = value.get("style", "-")
        self._emit_value_changed()

    def _emit_value_changed(self) -> None:
        self.changed.emit(self.get_value())

    def _on_property_changed(self, value: EdgePropertyDict):
        if value is None:
            return
        enabled = value["width"] > 0.0
        self._edge_color.enabled = enabled
        self._edge_style.enabled = enabled

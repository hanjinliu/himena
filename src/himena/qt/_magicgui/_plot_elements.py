from __future__ import annotations
from typing import Any, TYPE_CHECKING

from magicgui.types import Undefined
from magicgui.widgets import LineEdit, ComboBox
from magicgui.widgets.bases import ValuedContainerWidget, ValueWidget
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

    class AxisPropertyDict(TypedDict):
        lim: NotRequired[tuple[float, float]]
        scale: NotRequired[str]
        label: NotRequired[str]
        ticks: NotRequired[Any]
        grid: NotRequired[bool]


class ColorOrColorCycleEdit(ValuedContainerWidget):
    def __init__(self, value=Undefined, **kwargs):
        self._use_color_cycle = ToggleSwitch(value=False, text="use color cycle")
        self._color = ColorEdit(value="black")
        self._color_cycle = ColormapEdit(
            value="tab10",
            defaults=[
                "tab10",
                "tab10_colorblind",
                "tab20",
                "colorbrewer:Accent",
                "colorbrewer:Dark2",
                "colorbrewer:Paired",
                "colorbrewer:Pastel1",
                "colorbrewer:Pastel2",
                "colorbrewer:Set1",
                "colorbrewer:Set2",
                "colorbrewer:Set3",
            ],
            visible=False,
        )
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
        value = (
            self._color_cycle.value
            if self._use_color_cycle.value
            else self._color.value.hex
        )
        if value is None and not self._nullable:
            raise ValueError("Value cannot be None")
        return value

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


class LimitEdit(ValuedContainerWidget[tuple[float, float]]):
    def __init__(self, value=Undefined, **kwargs):
        self._min_widget = FloatEdit(value=0.0, label="min")
        self._max_widget = FloatEdit(value=1.0, label="max")
        super().__init__(
            value,
            widgets=[self._min_widget, self._max_widget],
            layout="horizontal",
            **kwargs,
        )
        self._min_widget.changed.connect(self._emit_value_changed)
        self._max_widget.changed.connect(self._emit_value_changed)
        self.margins = (0, 0, 0, 0)

    def get_value(self) -> tuple[float, float]:
        return self._min_widget.value, self._max_widget.value

    def set_value(self, value: tuple[float, float]):
        with self.changed.blocked():
            self._min_widget.value = value[0]
            self._max_widget.value = value[1]
        self._emit_value_changed()

    def _emit_value_changed(self) -> None:
        self.changed.emit(self.get_value())


class AxisPropertyEdit(ValuedContainerWidget["AxisPropertyDict"]):
    def __init__(self, value=Undefined, **kwargs):
        if value is None:
            value = Undefined
        self._lim_widget = LimitEdit(label="lim")
        self._scale_widget = ComboBox(choices=["linear", "log"], label="scale")
        self._label_widget = LineEdit(value="", label="label")
        self._grid_widget = ToggleSwitch(value=False, text="grid")
        super().__init__(
            value,
            widgets=[
                self._lim_widget,
                self._scale_widget,
                self._label_widget,
                self._grid_widget,
            ],
            **kwargs,
        )
        self._lim_widget.changed.connect(self._emit_value_changed)
        self._scale_widget.changed.connect(self._emit_value_changed)
        self._label_widget.changed.connect(self._emit_value_changed)
        self._grid_widget.changed.connect(self._emit_value_changed)

    def get_value(self) -> AxisPropertyDict:
        return {
            "lim": self._lim_widget.value,
            "scale": self._scale_widget.value,
            "label": self._label_widget.value,
            "grid": self._grid_widget.value,
        }

    def set_value(self, value: AxisPropertyDict):
        value = value or {}
        with self.changed.blocked():
            if (lim := value.get("lim", None)) is not None:
                self._lim_widget.value = tuple(lim)
            if "scale" in value:
                self._scale_widget.value = value["scale"]
            if (label := value.get("label", None)) is not None:
                self._label_widget.value = label
            if "grid" in value:
                self._grid_widget.value = value["grid"]
        self._emit_value_changed()

    def _emit_value_changed(self) -> None:
        self.changed.emit(self.get_value())


class DictEdit(ValuedContainerWidget[dict]):
    def __init__(self, options: dict[str, dict], value=Undefined, **kwargs):
        from himena.qt._magicgui import get_type_map

        type_map = get_type_map()
        self._widget_dict: dict[str, ValueWidget] = {}
        for k, opt in options.items():
            _opt = opt.copy()
            if (label := _opt.pop("label", None)) is None:
                label = k
            value = _opt.pop("value", Undefined)
            annotation = _opt.pop("annotation", None)
            self._widget_dict[k] = type_map.create_widget(
                value, annotation=annotation, options=_opt, label=label
            )
        super().__init__(value, widgets=self._widget_dict.values(), **kwargs)
        for widget in self._widget_dict.values():
            widget.changed.connect(self._emit_value_changed)

    def get_value(self) -> dict:
        return {k: v.value for k, v in self._widget_dict.items()}

    def set_value(self, value: dict):
        if value is None or value is Undefined:
            value = {}
        with self.changed.blocked():
            for k, v in value.items():
                if k in self._widget_dict:
                    self._widget_dict[k].value = v
        self.changed.emit(self.get_value())

    def _emit_value_changed(self) -> None:
        self.changed.emit(self.get_value())

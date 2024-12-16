from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore

from himena.standards import model_meta
from himena.qt._utils import qsignal_blocker


class QDimsSlider(QtW.QWidget):
    valueChanged = QtCore.Signal(tuple)

    def __init__(self):
        super().__init__()
        self._sliders: list[_QAxisSlider] = []
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        self._xy_axes: list[model_meta.ArrayAxis] = [
            model_meta.ArrayAxis(name="y"),
            model_meta.ArrayAxis(name="x"),
        ]

    def count(self) -> int:
        """Number of sliders."""
        return len(self._sliders)

    def set_dimensions(
        self,
        shape: tuple[int, ...],
        axes: list[model_meta.ArrayAxis],
        is_rgb: bool = False,
    ):
        ndim = len(shape)
        ndim_rem = ndim - 3 if is_rgb else ndim - 2
        nsliders = len(self._sliders)
        if nsliders > ndim_rem:
            for i in range(ndim_rem, nsliders):
                slider = self._sliders.pop()
                self.layout().removeWidget(slider)
                slider.deleteLater()
        elif nsliders < ndim_rem:
            for i in range(nsliders, ndim_rem):
                self._make_slider(shape[i])
        # update axis names
        _axis_width_max = 0
        _index_width_max = 0
        for axis, slider in zip(axes, self._sliders):
            aname = axis.name
            slider.update_from_axis(axis)
            # TODO: show scale, unit and origin
            width = slider._name_label.fontMetrics().width(aname)
            _axis_width_max = max(_axis_width_max, width)
            _i_max = slider._slider.maximum()
            width = slider._index_label.fontMetrics().width(f"{_i_max}/{_i_max}")
            _index_width_max = max(_index_width_max, width)
        for slider in self._sliders:
            slider._name_label.setFixedWidth(_axis_width_max + 6)
            slider._index_label.setFixedWidth(_index_width_max + 6)
        if is_rgb:
            self._xy_axes = axes[-3:-1]
        else:
            self._xy_axes = axes[-2:]

    def _to_image_axes(self) -> list[model_meta.ArrayAxis]:
        axes = [slider.to_axis() for slider in self._sliders]
        axes.extend(self._xy_axes)
        return axes

    def _make_slider(self, size: int) -> _QAxisSlider:
        slider = _QAxisSlider()
        self._sliders.append(slider)
        self.layout().addWidget(slider, alignment=QtCore.Qt.AlignmentFlag.AlignBottom)
        slider.setRange(0, size - 1)
        slider._slider.valueChanged.connect(self._emit_value)
        return slider

    def _emit_value(self):
        self.valueChanged.emit(self.value())

    def value(self) -> tuple[int, ...]:
        return tuple(slider._slider.value() for slider in self._sliders)

    def setValue(self, value: tuple[int, ...]) -> None:
        if len(value) != len(self._sliders):
            raise ValueError(f"Expected {len(self._sliders)} values, got {len(value)}")
        for slider, val in zip(self._sliders, value):
            with qsignal_blocker(slider):
                slider._slider.setValue(val)
        self.valueChanged.emit(value)

    def axis_names(self) -> list[str]:
        return [slider.text() for slider in self._sliders]


class _QAxisSlider(QtW.QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._name_label = QtW.QLabel()
        self._name_label.setFixedWidth(30)
        self._name_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self._slider = QtW.QScrollBar(QtCore.Qt.Orientation.Horizontal)
        self._slider.setSingleStep(1)
        self._slider.setPageStep(1)
        self._slider.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Fixed
        )

        self._index_label = QtW.QLabel()
        self._index_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self._slider.valueChanged.connect(self._on_slider_changed)

        layout.addWidget(self._name_label)
        layout.addWidget(self._slider)
        layout.addWidget(
            self._index_label, alignment=QtCore.Qt.AlignmentFlag.AlignRight
        )
        self._scale = 1.0
        self._unit = ""
        self._origin = 0.0

    def update_from_axis(self, axis: model_meta.ArrayAxis):
        self._name_label.setText(axis.name)
        self._scale = axis.scale if axis.scale is not None else 1.0
        self._unit = axis.unit
        self._origin = axis.origin

    def to_axis(self) -> model_meta.ArrayAxis:
        return model_meta.ArrayAxis(
            name=self.text(), scale=self._scale, unit=self._unit, origin=self._origin
        )

    def text(self) -> str:
        return self._name_label.text()

    def setText(self, text: str) -> None:
        self._name_label.setText(text)

    def setRange(self, start: int, end: int) -> None:
        self._slider.setRange(start, end)
        self._index_label.setText(f"{self._slider.value()}/{end}")

    def _on_slider_changed(self, value: int) -> None:
        self._index_label.setText(f"{value}/{self._slider.maximum()}")

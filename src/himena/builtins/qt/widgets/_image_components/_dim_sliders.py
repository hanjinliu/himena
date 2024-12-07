from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore
from himena._data_wrappers import ArrayWrapper

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

    def count(self) -> int:
        """Number of sliders."""
        return len(self._sliders)

    def _refer_array(
        self,
        arr: ArrayWrapper,
        axes: list[model_meta.ImageAxis],
        is_rgb: bool = False,
    ):
        ndim_rem = arr.ndim - 3 if is_rgb else arr.ndim - 2
        nsliders = len(self._sliders)
        if nsliders > ndim_rem:
            for i in range(ndim_rem, nsliders):
                slider = self._sliders.pop()
                self.layout().removeWidget(slider)
                slider.deleteLater()
        elif nsliders < ndim_rem:
            for i in range(nsliders, ndim_rem):
                self._make_slider(arr.shape[i])
        # update axis names
        _axis_width_max = 0
        _index_width_max = 0
        for axis, slider in zip(axes, self._sliders):
            aname = axis.name
            slider.setText(aname)
            # TODO: show scale, unit and origin
            width = slider._name_label.fontMetrics().width(aname)
            _axis_width_max = max(_axis_width_max, width)
            width = slider._index_label.fontMetrics().width(
                f"{arr.shape[i]}/{arr.shape[i]}"
            )
            _index_width_max = max(_index_width_max, width)
        for slider in self._sliders:
            slider._name_label.setFixedWidth(_axis_width_max + 6)
            slider._index_label.setFixedWidth(_index_width_max + 6)

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

    def text(self) -> str:
        return self._name_label.text()

    def setText(self, text: str) -> None:
        self._name_label.setText(text)

    def setRange(self, start: int, end: int) -> None:
        self._slider.setRange(start, end)
        self._index_label.setText(f"{self._slider.value()}/{end}")

    def _on_slider_changed(self, value: int) -> None:
        self._index_label.setText(f"{value}/{self._slider.maximum()}")

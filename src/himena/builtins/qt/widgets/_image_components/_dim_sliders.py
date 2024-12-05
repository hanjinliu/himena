from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore
from himena._data_wrappers import ArrayWrapper
from superqt import QLabeledSlider

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
        axes: list[str],
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
        _width_max = 0
        for aname, slider in zip(axes, self._sliders):
            slider.setText(aname)
            width = slider._label.fontMetrics().width(aname)
            _width_max = max(_width_max, width)
        for slider in self._sliders:
            slider._label.setFixedWidth(_width_max)

    def _make_slider(self, size: int) -> _QAxisSlider:
        slider = _QAxisSlider()
        self._sliders.append(slider)
        self.layout().addWidget(slider, alignment=QtCore.Qt.AlignmentFlag.AlignBottom)
        slider._slider.setRange(0, size - 1)
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
        self._label = QtW.QLabel()
        self._label.setFixedWidth(30)
        self._slider = QLabeledSlider(QtCore.Qt.Orientation.Horizontal)

        layout.addWidget(self._label)
        layout.addWidget(self._slider)

    def text(self) -> str:
        return self._label.text()

    def setText(self, text: str) -> None:
        self._label.setText(text)

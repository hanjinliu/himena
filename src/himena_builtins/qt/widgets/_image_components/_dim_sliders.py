from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore, QtGui

from himena.standards import model_meta
from himena.qt._utils import qsignal_blocker


class QDimsSlider(QtW.QWidget):
    """Dimension sliders for an array."""

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
            width = slider._name_label.fontMetrics().boundingRect(aname).width()
            _axis_width_max = max(_axis_width_max, width)
            _i_max = slider._slider.maximum()
            width = (
                slider._index_label.fontMetrics()
                .boundingRect(f"{_i_max}/{_i_max}")
                .width()
            )
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
        self.set_value_no_emit(value)
        self.valueChanged.emit(value)

    def set_value_no_emit(self, value: tuple[int, ...]) -> None:
        if len(value) != len(self._sliders):
            raise ValueError(f"Expected {len(self._sliders)} values, got {len(value)}")
        for slider, val in zip(self._sliders, value):
            with qsignal_blocker(slider):
                slider._slider.setValue(val)

    def axis_names(self) -> list[str]:
        return [slider._name_label.text() for slider in self._sliders]


class _QAxisSlider(QtW.QWidget):
    """A slider widget for an axis."""

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
        self._index_label.setCursor(QtCore.Qt.CursorShape.IBeamCursor)
        self._index_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self._slider.valueChanged.connect(self._on_slider_changed)

        layout.addWidget(self._name_label)
        layout.addWidget(self._slider)
        layout.addWidget(
            self._index_label, alignment=QtCore.Qt.AlignmentFlag.AlignRight
        )
        self._axis = model_meta.ArrayAxis(name="")
        self._edit_value_line = QCurrentIndexEdit(self)
        self._edit_value_line.setFont(self._index_label.font())
        self._edit_value_line.edited.connect(self._on_edit_finished)

    def update_from_axis(self, axis: model_meta.ArrayAxis):
        self._name_label.setText(axis.name)
        self._axis = axis.model_copy()

    def to_axis(self) -> model_meta.ArrayAxis:
        return self._axis

    def text(self) -> str:
        return self._name_label.text()

    def setRange(self, start: int, end: int) -> None:
        self._slider.setRange(start, end)
        self._index_label.setText(f"{self._slider.value()}/{end}")
        self._edit_value_line.setValidator(
            QtGui.QIntValidator(start, end, self._edit_value_line)
        )

    def _on_slider_changed(self, value: int) -> None:
        self._index_label.setText(f"{value}/{self._slider.maximum()}")

    def _on_edit_finished(self, value: int) -> None:
        self._slider.setValue(value)
        self._index_label.setText(f"{value}/{self._slider.maximum()}")

    def mouseDoubleClickEvent(self, a0):
        if self._index_label.geometry().contains(a0.pos()):
            self._edit_value_line._double_clicked(self._index_label)
        else:
            return super().mouseDoubleClickEvent(a0)


class QCurrentIndexEdit(QtW.QLineEdit):
    """A line edit for current index."""

    edited = QtCore.Signal(int)

    def __init__(self, parent: QtW.QWidget):
        super().__init__()
        self.setParent(
            parent,
            QtCore.Qt.WindowType.Dialog | QtCore.Qt.WindowType.FramelessWindowHint,
        )
        self.hide()
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

    def _finish_edit(self):
        self.edited.emit(int(self.text()))
        self._cancel_edit()

    def _cancel_edit(self):
        self.hide()
        self.parentWidget().setFocus()

    def _double_clicked(self, label: QtW.QLabel):
        self.show()
        current, _max = label.text().split("/", 1)
        dx = self.fontMetrics().boundingRect(f"/{_max}").width() + 1
        size = label.size()
        self.resize(size.width() - dx, size.height())
        geo = label.geometry()
        self.move(self.parentWidget().mapToGlobal(geo.topLeft()))
        self.setText(current)
        self.setSelection(0, len(self.text()))

    def focusOutEvent(self, a0):
        self._finish_edit()
        return super().focusOutEvent(a0)

    def keyPressEvent(self, a0):
        if a0.key() == QtCore.Qt.Key.Key_Return:
            self._finish_edit()
        elif a0.key() == QtCore.Qt.Key.Key_Escape:
            self._cancel_edit()
        else:
            return super().keyPressEvent(a0)

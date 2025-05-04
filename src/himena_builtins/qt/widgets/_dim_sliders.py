from __future__ import annotations
from typing import Literal

from qtpy import QtWidgets as QtW, QtCore, QtGui
from magicgui import widgets as mgw
from himena.standards import model_meta
from himena.qt._utils import qsignal_blocker
from himena.consts import MonospaceFontFamily


class QDimsSlider(QtW.QWidget):
    """Dimension sliders for an array."""

    valueChanged = QtCore.Signal(tuple)

    def __init__(self):
        super().__init__()
        self._sliders: list[_QAxisSlider] = []
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        self._yx_axes: list[model_meta.DimAxis] = [
            model_meta.DimAxis(name="y"),
            model_meta.DimAxis(name="x"),
        ]

    def count(self) -> int:
        """Number of sliders."""
        return len(self._sliders)

    def maximums(self) -> tuple[int, ...]:
        """Return the maximum values of the sliders."""
        return tuple(slider._slider.maximum() for slider in self._sliders)

    def set_dimensions(
        self,
        shape: tuple[int, ...],
        axes: list[model_meta.DimAxis] | None = None,
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
        if axes is None:
            axes = [model_meta.DimAxis(name=f"axis {i}") for i in range(ndim_rem)]
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
            self._yx_axes = axes[-3:-1]
        else:
            self._yx_axes = axes[-2:]

    def to_dim_axes(self) -> list[model_meta.DimAxis]:
        axes = [slider.to_axis() for slider in self._sliders]
        axes.extend(self._yx_axes)
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
            if val == -1:  # flattened axis, no need to update slider
                continue
            with qsignal_blocker(slider):
                slider._slider.setValue(val)

    def axis_names(self) -> list[str]:
        return [slider._name_label.text() for slider in self._sliders]


class _QSliderButton(QtW.QPushButton):
    """A button for the slider."""

    def __init__(self, text: str):
        super().__init__(text)
        self.setStyleSheet("_QSliderButton { padding: 0px; margin: 0px}")
        self.setFixedSize(12, 12)
        font = QtGui.QFont(MonospaceFontFamily, 8)
        self.setFont(font)
        self.setAutoRepeat(True)
        self.setAutoDefault(False)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)


class _QAxisSlider(QtW.QWidget):
    """A slider widget for an axis."""

    def __init__(self) -> None:
        super().__init__()
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._name_label = QtW.QLabel()
        self._name_label.setFixedWidth(60)
        self._name_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self._play_btn = _QSliderButton("▶")
        self._play_btn.setToolTip("Play along this axis (right click to configure)")
        self._play_btn.setCheckable(True)
        self._play_btn.setAutoRepeat(False)
        self._play_btn.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu
        )
        self._play_btn.customContextMenuRequested.connect(
            lambda pos: self._make_context_menu_for_play_btn().exec(
                self._play_btn.mapToGlobal(pos)
            )
        )
        self._play_timer = QtCore.QTimer(self)
        self._play_timer.setInterval(100)
        self._play_timer.timeout.connect(self._on_play_timer_timeout)
        self._play_back_mode: Literal["once", "loop", "pingpong"] = "loop"
        self._play_increment = 1
        self._play_btn.clicked.connect(self._on_play_clicked)

        self._prev_btn = _QSliderButton("<")
        self._prev_btn.clicked.connect(self._on_prev_clicked)

        self._slider = QtW.QScrollBar(QtCore.Qt.Orientation.Horizontal)
        self._slider.setContentsMargins(0, 0, 0, 0)
        self._slider.setSingleStep(1)
        self._slider.setPageStep(1)
        self._slider.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Fixed
        )
        self._next_btn = _QSliderButton(">")
        self._next_btn.clicked.connect(self._on_next_clicked)
        self._index_label = QtW.QLabel()
        self._index_label.setCursor(QtCore.Qt.CursorShape.IBeamCursor)
        self._index_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self._slider.valueChanged.connect(self._on_slider_changed)

        layout.addWidget(self._name_label)
        layout.addWidget(self._play_btn)
        layout.addWidget(self._prev_btn)
        layout.addWidget(self._slider)
        layout.addWidget(self._next_btn)
        layout.addWidget(
            self._index_label, alignment=QtCore.Qt.AlignmentFlag.AlignRight
        )
        self._axis = model_meta.DimAxis(name="")
        self._edit_value_line = QCurrentIndexEdit(self)
        self._edit_value_line.setFont(self._index_label.font())
        self._edit_value_line.edited.connect(self._on_edit_finished)

    def update_from_axis(self, axis: model_meta.DimAxis):
        self._name_label.setText(axis.name)
        self._axis = axis.model_copy()

    def to_axis(self) -> model_meta.DimAxis:
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

    def _on_prev_clicked(self):
        self._stop_play()
        self._slider.setValue(max(self._slider.value() - 1, 0))

    def _on_next_clicked(self):
        self._stop_play()
        self._slider.setValue(min(self._slider.value() + 1, self._slider.maximum()))

    def _on_play_timer_timeout(self):
        if self._play_btn.isChecked():
            new_value = self._slider.value() + self._play_increment
            if new_value > self._slider.maximum():
                if self._play_back_mode == "loop":
                    new_value = 0
                elif self._play_back_mode == "pingpong":
                    new_value = self._slider.maximum() - 1
                    self._play_increment = -self._play_increment
                else:
                    self._stop_play()
            elif new_value < 0:
                if self._play_back_mode == "loop":
                    new_value = self._slider.maximum()
                elif self._play_back_mode == "pingpong":
                    new_value = 1
                    self._play_increment = -self._play_increment
                else:
                    self._stop_play()
            self._slider.setValue(new_value)

    def _stop_play(self):
        self._play_btn.setChecked(False)
        self._play_timer.stop()

    def _on_play_clicked(self):
        if self._play_btn.isChecked():
            self._play_timer.start()
        else:
            self._play_timer.stop()

    def _make_context_menu_for_play_btn(self) -> QtW.QMenu:
        menu = QtW.QMenu(self)
        direction = mgw.ComboBox(
            label="Direction",
            choices=[("forward", 1), ("backward", -1)],
            value=1,
        )
        fps = mgw.FloatSpinBox(
            label="FPS",
            min=0.1,
            max=100.0,
            value=1000 / self._play_timer.interval(),
            step=10,
        )
        loop = mgw.ComboBox(
            label="Mode",
            choices=["once", "loop", "pingpong"],
            value=self._play_back_mode,
        )
        container = mgw.Container(widgets=[direction, fps, loop])
        fps.changed.connect(lambda v: self._play_timer.setInterval(int(1000 / v)))
        loop.changed.connect_setattr(self, "_play_back_mode", maxargs=1)
        direction.changed.connect_setattr(self, "_play_increment", maxargs=1)
        widget_action = QtW.QWidgetAction(menu)
        widget_action.setDefaultWidget(container.native)
        menu.addAction(widget_action)
        return menu


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
        """Start editing the current index."""
        self.show()
        current, _max = label.text().split("/", 1)
        dx = self.fontMetrics().boundingRect(f"/{_max}").width() + 1
        size = label.size()
        self.resize(size.width() - dx, size.height())
        geo = label.geometry()
        self.move(self.parentWidget().mapToGlobal(geo.topLeft()))
        self.setText(current)
        self.setFocus()
        self.selectAll()

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

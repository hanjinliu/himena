from __future__ import annotations
from typing import Any

from qtpy import QtWidgets as QtW, QtCore, QtGui
from himena.consts import StandardType, ParametricWidgetProtocolNames as PWPN
from himena.types import WidgetDataModel
from himena.plugins import validate_protocol
from magicgui import widgets as mgw


class QParametricWidget(QtW.QWidget):
    """QWidget that contain a magicgui Container and a button to run functions."""

    __himena_display_name__ = "Parametric Widget"

    param_changed = QtCore.Signal()

    def __init__(self, central: QtW.QWidget | mgw.Widget) -> None:
        super().__init__()
        self._scroll_area = QtW.QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding
        )
        self._scroll_area.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._call_btn = QtW.QPushButton("Run", self)
        self._central_widget = central
        layout_h = QtW.QHBoxLayout(self)
        layout_h.setContentsMargins(0, 0, 0, 0)
        layout_h.addWidget(self._scroll_area)
        area_widget = QtW.QWidget()
        self._scroll_area.setWidget(area_widget)
        layout_v = QtW.QVBoxLayout(area_widget)
        layout_v.setContentsMargins(4, 4, 4, 4)
        layout_v.setSpacing(2)
        if isinstance(central, mgw.Widget):
            if not isinstance(central.native, QtW.QWidget):
                raise ValueError(f"Expected a QWidget, got {central}")
            self._central_qwidget = central.native
        else:
            self._central_qwidget = central
        layout_v.addWidget(self._central_qwidget)
        layout_v.addWidget(self._call_btn)
        if connector := getattr(central, PWPN.CONNECT_CHANGED_SIGNAL, None):
            connector(self._on_param_changed)
        if hasattr(central, "__himena_model_track__"):
            self.__himena_model_track__ = central.__himena_model_track__
        self._result_widget: QtW.QWidget | None = None

        self._control = QtW.QWidget()
        control_layout = QtW.QHBoxLayout(self._control)
        control_layout.setContentsMargins(0, 0, 0, 0)
        self._central_widget_size_hint = self._central_qwidget.sizeHint()
        if isinstance(central, mgw.Container):
            # find the proper size hint
            min_height = sum(max(each.min_height, 28) for each in central) + 2 * (
                len(central) - 1
            )
            min_width = max(max(each.min_width, 80) for each in central) + 6
            self._central_widget_size_hint.setHeight(
                max(self._central_widget_size_hint.height(), min_height)
            )
            self._central_widget_size_hint.setWidth(
                max(self._central_widget_size_hint.width(), min_width)
            )
        self._layout_v = layout_v
        self._layout_h = layout_h
        self._result_widget_layout: QtW.QLayout | None = None
        self.setMinimumWidth(100)

    def get_params(self) -> dict[str, Any]:
        return getattr(self._central_widget, PWPN.GET_PARAMS)()

    @validate_protocol
    def to_model(self) -> WidgetDataModel[dict[str, Any]]:
        params = self.get_params()
        return WidgetDataModel(value=params, type=StandardType.DICT)

    @validate_protocol
    def model_type(self: QtW.QWidget) -> str:
        return StandardType.DICT

    @validate_protocol
    def size_hint(self) -> tuple[int, int] | None:
        mysize = self._base_size_hint()
        if self._result_widget is None:
            return mysize.width(), min(mysize.height(), 400)
        if hasattr(self._result_widget, "size_hint") and (
            size := self._result_widget.size_hint()
        ):
            w0, h0 = size
        else:
            hint = self._result_widget.sizeHint()
            w0, h0 = hint.width(), hint.height()
        mysize.setHeight(mysize.height() + h0)
        mysize.setWidth(max(mysize.width(), w0))
        return mysize.width(), min(mysize.height(), 400)

    @validate_protocol
    def control_widget(self) -> QtW.QWidget:
        return self._control

    def keyPressEvent(self, a0: QtGui.QKeyEvent | None) -> None:
        if a0 and a0.key() == QtCore.Qt.Key.Key_Return:
            self._call_btn.click()
        return super().keyPressEvent(a0)

    def _base_size_hint(self) -> QtCore.QSize:
        mysize = QtCore.QSize(self._central_widget_size_hint)
        mysize.setWidth(max(mysize.width() + 10, 80))  # content margins
        mysize.setHeight(mysize.height() + 36)  # content margins and scroll area
        if self._call_btn.isVisible():
            mysize.setHeight(mysize.height() + 24)  # button height
        return mysize

    def setFocus(self) -> None:
        if (
            isinstance(self._central_widget, mgw.Container)
            and len(self._central_widget) > 0
        ):
            # focus the first input
            return self._central_widget[0].native.setFocus()
        else:
            return super().setFocus()

    def _on_param_changed(self) -> None:
        self.param_changed.emit()

    def is_preview_enabled(self) -> bool:
        if isfunc := getattr(self._central_widget, PWPN.IS_PREVIEW_ENABLED, None):
            return isfunc()
        return False

    def add_widget_below(self, widget: QtW.QWidget) -> None:
        self._layout_v.addWidget(widget)
        self._result_widget = widget
        self._result_widget_layout = self._layout_v
        if hasattr(widget, "control_widget"):
            self._control.layout().addWidget(widget.control_widget())

    def add_widget_right(self, widget: QtW.QWidget) -> None:
        self._layout_h.addWidget(widget)
        self._result_widget = widget
        self._result_widget_layout = self._layout_h
        if hasattr(widget, "control_widget"):
            self._control.layout().addWidget(widget.control_widget())

    def remove_result_widget(self) -> None:
        if self._result_widget is not None:
            if self._result_widget_layout is not None:
                self._result_widget_layout.removeWidget(self._result_widget)
            self._result_widget = None
            self._result_widget_layout = None
        if self._control.layout().count() > 0:
            self._control.layout().itemAt(0).widget().setParent(None)

    def set_busy(self, busy: bool):
        if busy:
            self._call_btn.setText("Running ...")
            self._call_btn.setEnabled(False)
        else:
            self._call_btn.setText("Run")
            self._call_btn.setEnabled(True)

from __future__ import annotations
from typing import Any

from PyQt5.QtGui import QKeyEvent
from qtpy import QtWidgets as QtW, QtCore
from himena.consts import StandardType, ParametricWidgetProtocolNames as PWPN
from himena.types import WidgetDataModel
from himena.plugins import protocol_override
from magicgui.widgets import Widget, Container


class QParametricWidget(QtW.QWidget):
    """QWidget that contain a magicgui Container and a button to run functions."""

    param_changed = QtCore.Signal()

    def __init__(self, central: QtW.QWidget | Widget) -> None:
        super().__init__()
        self._call_btn = QtW.QPushButton("Run", self)
        self._central_widget = central
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)
        if isinstance(central, Widget):
            if not isinstance(central.native, QtW.QWidget):
                raise ValueError(f"Expected a QWidget, got {central}")
            self._central_qwidget = central.native
        else:
            self._central_qwidget = central
        layout.addWidget(self._central_qwidget)
        layout.addWidget(self._call_btn)
        if connector := getattr(central, PWPN.CONNECT_CHANGED_SIGNAL, None):
            connector(self._on_param_changed)
        if hasattr(central, "__himena_model_track__"):
            self.__himena_model_track__ = central.__himena_model_track__
        self._result_widget: QtW.QWidget | None = None

        self._control = QtW.QWidget()
        control_layout = QtW.QHBoxLayout(self._control)
        control_layout.setContentsMargins(0, 0, 0, 0)
        self._central_widget_size_hint = self._central_qwidget.sizeHint()
        if isinstance(central, Container):
            min_height = sum(max(each.min_height, 28) for each in central) + 2 * (
                len(central) - 1
            )
            self._central_widget_size_hint.setHeight(
                max(self._central_widget_size_hint.height(), min_height)
            )

    def get_params(self) -> dict[str, Any]:
        return getattr(self._central_widget, PWPN.GET_PARAMS)()

    @protocol_override
    def to_model(self) -> WidgetDataModel[dict[str, Any]]:
        params = self.get_params()
        return WidgetDataModel(value=params, type=StandardType.DICT)

    @protocol_override
    def model_type(self: QtW.QWidget) -> str:
        return StandardType.DICT

    @protocol_override
    def size_hint(self) -> tuple[int, int] | None:
        mysize = self._base_size_hint()
        if self._result_widget is None:
            return mysize.width(), mysize.height()
        if hasattr(self._result_widget, "size_hint") and (
            size := self._result_widget.size_hint()
        ):
            w0, h0 = size
        else:
            hint = self._result_widget.sizeHint()
            w0, h0 = hint.width(), hint.height()
        mysize.setHeight(mysize.height() + h0)
        mysize.setWidth(max(mysize.width(), w0))
        return mysize.width(), mysize.height()

    @protocol_override
    def control_widget(self) -> QtW.QWidget:
        return self._control

    def keyPressEvent(self, a0: QKeyEvent | None) -> None:
        if a0 and a0.key() == QtCore.Qt.Key.Key_Return:
            self._call_btn.click()
        return super().keyPressEvent(a0)

    def _base_size_hint(self) -> QtCore.QSize:
        mysize = QtCore.QSize(self._central_widget_size_hint)
        mysize.setWidth(mysize.width() + 6)  # content margins
        mysize.setHeight(mysize.height() + 6)  # content margins
        if self._call_btn.isVisible():
            mysize.setHeight(mysize.height() + 24)  # button height
        return mysize

    def setFocus(self) -> None:
        if (
            isinstance(self._central_widget, Container)
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
        layout = self.layout()
        layout.addWidget(widget)
        self._result_widget = widget
        if hasattr(widget, "control_widget"):
            self._control.layout().addWidget(widget.control_widget())

    def remove_widget_below(self) -> None:
        layout = self.layout()
        if self._result_widget is not None:
            layout.removeWidget(self._result_widget)
            self._result_widget = None
        if self._control.layout().count() > 0:
            self._control.layout().itemAt(0).widget().setParent(None)

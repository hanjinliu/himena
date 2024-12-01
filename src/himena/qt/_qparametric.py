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
        if isinstance(central, Widget):
            self._central_qwidget = central.native
        else:
            self._central_qwidget = central
        layout.addWidget(self._central_qwidget)
        layout.addWidget(self._call_btn)
        if connector := getattr(central, PWPN.CONNECT_CHANGED_SIGNAL, None):
            connector(self._on_param_changed)
        if hasattr(central, "__himena_model_track__"):
            self.__himena_model_track__ = central.__himena_model_track__

    def get_params(self) -> dict[str, Any]:
        return getattr(self._central_widget, PWPN.GET_PARAMS)()

    @protocol_override
    def to_model(self) -> WidgetDataModel[dict[str, Any]]:
        params = self.get_params()
        return WidgetDataModel(value=params, type=StandardType.DICT)

    @protocol_override
    def model_type(self: QtW.QWidget) -> str:
        return StandardType.DICT

    def keyPressEvent(self, a0: QKeyEvent | None) -> None:
        if a0 and a0.key() == QtCore.Qt.Key.Key_Return:
            self._call_btn.click()
        return super().keyPressEvent(a0)

    def setFocus(self) -> None:
        if (
            isinstance(self._central_widget, Container)
            and len(self._central_widget) > 0
        ):
            return self._central_widget[0].native.setFocus()
        else:
            return super().setFocus()

    def _on_param_changed(self) -> None:
        self.param_changed.emit()

    def is_preview_enabled(self) -> bool:
        if isfunc := getattr(self._central_widget, PWPN.IS_PREVIEW_ENABLED, None):
            return isfunc()
        return False

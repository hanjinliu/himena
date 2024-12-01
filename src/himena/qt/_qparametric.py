from __future__ import annotations
from typing import Any

from qtpy import QtWidgets as QtW, QtCore
from himena.consts import StandardType, ParametricWidgetProtocolNames as PWPN
from himena.types import WidgetDataModel
from magicgui.widgets import Widget


class QParametricWidget(QtW.QWidget):
    param_changed = QtCore.Signal()

    def __init__(self, central: QtW.QWidget | Widget) -> None:
        super().__init__()
        self._call_btn = QtW.QPushButton("Run", self)
        self._central_widget = central
        layout = QtW.QVBoxLayout(self)
        if isinstance(central, Widget):
            layout.addWidget(central.native)
        else:
            layout.addWidget(central)
        layout.addWidget(self._call_btn)
        if connector := getattr(central, PWPN.CONNECT_CHANGED_SIGNAL, None):
            connector(self._on_param_changed)
        if hasattr(central, "__himena_model_track__"):
            self.__himena_model_track__ = central.__himena_model_track__

    def get_params(self) -> dict[str, Any]:
        return getattr(self._central_widget, PWPN.GET_PARAMS)()

    def to_model(self) -> WidgetDataModel[dict[str, Any]]:
        params = self.get_params()
        return WidgetDataModel(value=params, type=StandardType.DICT)

    def model_type(self: QtW.QWidget) -> str:
        return StandardType.DICT

    def _on_param_changed(self) -> None:
        self.param_changed.emit()

    def is_preview_enabled(self) -> bool:
        if isfunc := getattr(self._central_widget, PWPN.IS_PREVIEW_ENABLED, None):
            return isfunc()
        return False

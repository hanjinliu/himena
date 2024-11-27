from __future__ import annotations
from typing import Any

from qtpy import QtWidgets as QtW, QtCore
from himena.consts import StandardType, ParametricWidgetProtocolNames as PWPN
from himena.types import WidgetDataModel


class QParametricWidget(QtW.QWidget):
    param_changed = QtCore.Signal()

    def __init__(self, central: QtW.QWidget) -> None:
        super().__init__()
        self._call_btn = QtW.QPushButton("Run", self)
        self._central_widget = central
        layout = QtW.QVBoxLayout(self)
        layout.addWidget(central)
        layout.addWidget(self._call_btn)
        if connector := getattr(central, PWPN.CONNECT_CHANGED_SIGNAL, None):
            connector(self._on_param_changed)

    def get_params(self) -> dict[str, Any]:
        return getattr(self._central_widget, PWPN.GET_PARAMS)()

    def to_model(self) -> WidgetDataModel[dict[str, Any]]:
        params = self.get_params()
        return WidgetDataModel(value=params, type=StandardType.PARAMETERS)

    def model_type(self: QtW.QWidget) -> str:
        return StandardType.PARAMETERS

    def _on_param_changed(self) -> None:
        self.param_changed.emit()

    def is_preview_enabled(self) -> bool:
        if isfunc := getattr(self._central_widget, PWPN.IS_PREVIEW_ENABLED, None):
            return isfunc()
        return False

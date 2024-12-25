from __future__ import annotations

from qtpy import QtWidgets as QtW, QtGui
from himena.types import WidgetDataModel
from himena.consts import MonospaceFontFamily
from himena.plugins import validate_protocol


class QFallbackWidget(QtW.QPlainTextEdit):
    """A fallback widget for the data of non-registered type."""

    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFont(QtGui.QFont(MonospaceFontFamily))
        self._model: WidgetDataModel | None = None

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        self.setPlainText(f"type: {model.type!r}\nvalue:\n{model.value!r}")
        self._model = model
        return

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        if self._model is None:
            raise ValueError("Model is not set")
        return self._model

    @validate_protocol
    def model_type(self) -> str:
        return self._model.type

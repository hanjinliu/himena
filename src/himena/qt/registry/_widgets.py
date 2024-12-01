from __future__ import annotations

from qtpy import QtWidgets as QtW, QtGui
from himena.types import WidgetDataModel
from himena.consts import MonospaceFontFamily
from himena.plugins import protocol_override


class QFallbackWidget(QtW.QPlainTextEdit):
    """A fallback widget for the data of non-registered type."""

    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFont(QtGui.QFont(MonospaceFontFamily))
        self._model: WidgetDataModel | None = None

    @protocol_override
    def update_model(self, model: WidgetDataModel):
        self.setPlainText(
            f"No widget registered for:\n\ntype: {model.type!r}\nvalue:\n{model.value!r}"
        )
        self._model = model
        return

    @protocol_override
    def to_model(self) -> WidgetDataModel:
        if self._model is None:
            raise ValueError("Model is not set")
        return self._model

    @protocol_override
    def model_type(self) -> str:
        return self._model.type

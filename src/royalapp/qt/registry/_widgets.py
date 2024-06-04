from __future__ import annotations

from qtpy import QtWidgets as QtW, QtGui
from royalapp.types import WidgetDataModel
from royalapp.qt._qt_consts import MonospaceFontFamily


class QFallbackWidget(QtW.QPlainTextEdit):
    """A fallback widget for the data of non-registered type."""

    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFont(QtGui.QFont(MonospaceFontFamily))

    @classmethod
    def from_model(cls, model: WidgetDataModel) -> QFallbackWidget:
        self = cls()
        self.setPlainText(
            f"No widget registered for:\n\ntype: {model.type!r}\nvalue: {model.value!r}"
        )
        return self

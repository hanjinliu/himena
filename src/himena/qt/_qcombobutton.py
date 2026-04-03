from __future__ import annotations
from typing import Iterable, Callable

from qtpy import QtCore, QtWidgets as QtW


class QComboButton(QtW.QToolButton):
    currentTextChanged = QtCore.Signal(str)

    def __init__(self, text: str = "", parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)
        self._choices: Callable[[], Iterable[str]] = lambda: []
        self.clicked.connect(self._on_clicked)
        self._title = ""
        self._message = ""
        self._formatter = "{}"
        self._current_text = ""
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setCurrentText(text)

    def _on_clicked(self):
        from himena.widgets import current_instance

        resp = current_instance().exec_choose_one_dialog(
            title=self._title,
            message=self._message,
            choices=self._choices(),
            how="palette",
        )
        if resp is not None:
            self.setCurrentText(str(resp))
            self.currentTextChanged.emit(str(resp))

    def currentText(self) -> str:
        return self._current_text

    def setCurrentText(self, text: str) -> None:
        self.setText(self._formatter.format(text))
        self._current_text = text

    def setTitle(self, title: str) -> None:
        self._title = title

    def setMessage(self, message: str) -> None:
        self._message = message

    def setFormatter(self, formatter: str) -> None:
        self._formatter = formatter
        self.setCurrentText(self._current_text)

    def setChoices(self, choices: Iterable[str] | Callable[[], Iterable[str]]) -> None:
        if callable(choices):
            self._choices = choices
        else:
            self._choices = lambda: choices

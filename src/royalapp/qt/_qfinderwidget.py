from __future__ import annotations

from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtCore import Qt
from typing import TYPE_CHECKING, Generic, TypeVar

_W = TypeVar("_W", bound=QtW.QPlainTextEdit)


class QFinderWidget(QtW.QDialog, Generic[_W]):
    """A finder widget for a text editor."""

    def __init__(self, parent: _W | None = None):
        super().__init__(parent, Qt.WindowType.SubWindow)
        _layout = QtW.QHBoxLayout(self)
        _layout.setContentsMargins(2, 2, 2, 2)
        self.setLayout(_layout)
        _line = QtW.QLineEdit()
        _btn_prev = QtW.QPushButton("▲")
        _btn_next = QtW.QPushButton("▼")
        _btn_prev.setFixedSize(18, 18)
        _btn_next.setFixedSize(18, 18)
        _layout.addWidget(_line)
        _layout.addWidget(_btn_prev)
        _layout.addWidget(_btn_next)
        _btn_prev.clicked.connect(self._find_prev)
        _btn_next.clicked.connect(self._find_next)
        _line.textChanged.connect(self._find_next)
        self._line_edit = _line

    # fmt: off
    if TYPE_CHECKING:
        def parentWidget(self) -> _W: ...
    # fmt: on

    def lineEdit(self) -> QtW.QLineEdit:
        return self._line_edit

    def _find_prev(self):
        text = self._line_edit.text()
        if text == "":
            return
        qtext = self.parentWidget()
        flag = QtGui.QTextDocument.FindFlag.FindBackward
        found = qtext.find(text, flag)
        if not found:
            qtext.moveCursor(QtGui.QTextCursor.MoveOperation.End)
            qtext.find(text, flag)

    def _find_next(self):
        text = self._line_edit.text()
        if text == "":
            return
        qlogger = self.parentWidget()
        found = qlogger.find(text)
        if not found:
            qlogger.moveCursor(QtGui.QTextCursor.MoveOperation.Start)
            qlogger.find(text)

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        if a0.key() == Qt.Key.Key_Escape:
            self.hide()
            self.parentWidget().setFocus()
        elif a0.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return):
            if a0.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self._find_prev()
            else:
                self._find_next()
        return super().keyPressEvent(a0)

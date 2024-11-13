from __future__ import annotations

from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtCore import Qt
from typing import TYPE_CHECKING, Generic, TypeVar
import itertools

_W = TypeVar("_W", bound=QtW.QPlainTextEdit)
_X = TypeVar("_W", bound=QtW.QWidget)


class _QFinderBaseWidget(QtW.QDialog, Generic[_X]):
    def __init__(self, parent: _W):
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
        _btn_prev.clicked.connect(self._btn_prev_clicked)
        _btn_next.clicked.connect(self._btn_next_clicked)
        _line.textChanged.connect(self._find_update)
        self._line_edit = _line
        self._btn_prev = _btn_prev
        self._btn_next = _btn_next
        self._parent_widget = parent

    # fmt: off
    if TYPE_CHECKING:
        def parentWidget(self) -> _W: ...
    # fmt: on

    def show(self):
        super().show()
        self._line_edit.setFocus()

    def _btn_prev_clicked(self):
        self._find_prev()
        self._line_edit.setFocus()

    def _btn_next_clicked(self):
        self._find_next()
        self._line_edit.setFocus()

    def _find_prev(self):
        raise NotImplementedError

    def _find_next(self):
        raise NotImplementedError

    def _find_update(self):
        raise NotImplementedError

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


class QFinderWidget(_QFinderBaseWidget[_W]):
    """A finder widget for a text editor."""

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
        qtext = self.parentWidget()
        found = qtext.find(text)
        if not found:
            qtext.moveCursor(QtGui.QTextCursor.MoveOperation.Start)
            qtext.find(text)

    _find_update = _find_next


class QTableFinderWidget(_QFinderBaseWidget[QtW.QTableView]):
    def _find_prev(self):
        line_text = self._line_edit.text()
        if line_text == "":
            return
        i, nr, nc = self._get_current_state()
        i -= 1

        for ith in itertools.chain(range(i, -1, -1), range(nr * nc - 1, i, -1)):
            if self._run_until_found(line_text, ith, nc):
                return

    def _find_next(self):
        line_text = self._line_edit.text()
        if line_text == "":
            return
        i, nr, nc = self._get_current_state()
        i += 1

        for ith in itertools.chain(range(i, nr * nc), range(i)):
            if self._run_until_found(line_text, ith, nc):
                return

    def _find_update(self):
        line_text = self._line_edit.text()
        if line_text == "":
            return
        i, nr, nc = self._get_current_state()

        for ith in itertools.chain(range(i, nr * nc), range(i)):
            if self._run_until_found(line_text, ith, nc):
                return

    def _get_current_state(self) -> tuple[int, int, int]:
        qtable = self._parent_widget
        index = qtable.currentIndex()
        model = qtable.model()
        i = index.row() * model.columnCount() + index.column()
        nr, nc = model.rowCount(), model.columnCount()
        return i, nr, nc

    def _run_until_found(self, line_text: str, ith: int, nc: int) -> bool:
        r, c = divmod(ith, nc)
        model = self._parent_widget.model()
        index = model.index(r, c)
        displayed: str = model.data(index, Qt.ItemDataRole.DisplayRole)
        if not isinstance(displayed, str):
            return False

        if displayed == "":
            return False
        if line_text in displayed:
            self._parent_widget.setCurrentIndex(index)
            return True
        return False

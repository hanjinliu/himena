from __future__ import annotations
import sys
from contextlib import suppress

from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtCore import Qt, Signal
from royalapp.qt._qfinderwidget import QFinderWidget


class QLogger(QtW.QPlainTextEdit):
    process = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setReadOnly(True)
        self.setWordWrapMode(QtGui.QTextOption.WrapMode.NoWrap)
        self.process.connect(self.update_text)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self._finder_widget = None

    def update_text(self, obj):
        self.moveCursor(QtGui.QTextCursor.MoveOperation.End)
        self.insertPlainText(obj)
        self.moveCursor(QtGui.QTextCursor.MoveOperation.End)
        return None

    def appendText(self, text: str):
        """Append text in the main thread."""
        self._emit_output(text)

    def _emit_output(self, text: str):
        with suppress(RuntimeError, OSError):
            self.process.emit(text)

    def _find_string(self):
        if self._finder_widget is None:
            self._finder_widget = QFinderWidget(self)
        self._finder_widget.show()
        self._finder_widget.lineEdit().setFocus()
        self._align_finder()

    def resizeEvent(self, event):
        if self._finder_widget is not None:
            self._align_finder()
        super().resizeEvent(event)

    def _align_finder(self):
        if fd := self._finder_widget:
            vbar = self.verticalScrollBar()
            if vbar.isVisible():
                fd.move(self.width() - fd.width() - vbar.width() - 3, 5)
            else:
                fd.move(self.width() - fd.width() - 3, 5)

    def keyPressEvent(self, e: QtGui.QKeyEvent | None) -> None:
        if (
            e.key() == Qt.Key.Key_F
            and e.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self._find_string()
            return None
        return super().keyPressEvent(e)


class StdoutInterface:
    def __init__(self):
        self._queue: list[str] = []
        self._widget = QLogger()

    def write(self, msg) -> None:
        """Handle the print event."""
        # self._queue.append(msg)
        self._widget.appendText(msg)
        return None

    def flush(self):
        """Do nothing."""

    def connect(self):
        sys.stdout = self
        sys.stderr = self

    def disconnect(self):
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__


_INTERFACES = {}


def get_interface(id: str = "default") -> StdoutInterface:
    if id in _INTERFACES:
        return _INTERFACES[id]
    interf = StdoutInterface()
    interf.connect()
    _INTERFACES[id] = interf
    return interf

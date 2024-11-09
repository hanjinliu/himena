from __future__ import annotations
import sys
from contextlib import suppress

import logging
from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtCore import Qt, Signal
from himena.qt._qfinderwidget import QFinderWidget
from himena.qt._qt_consts import MonospaceFontFamily


class QLogger(QtW.QPlainTextEdit):
    process = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setFont(QtGui.QFont(MonospaceFontFamily, 10))
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


class QtOutputWidget(QtW.QTabWidget):
    def __init__(self):
        super().__init__()
        self._stdout = QLogger()
        self._logger = QLogger()
        self.addTab(self._stdout, "stdout")
        self.addTab(self._logger, "log")


class OutputInterface(logging.Handler):
    def __init__(self):
        super().__init__()
        self._widget = QtOutputWidget()
        logger = logging.getLogger()
        self._default_handlers = logger.handlers
        logger.setLevel(logging.INFO)

    def write(self, msg) -> None:
        """Handle the print event."""
        self._widget._stdout.appendText(msg)
        return None

    def flush(self):
        """Do nothing."""

    def emit(self, record: logging.LogRecord):
        """Handle the logging event."""
        log_entry = self.format(record)
        self._widget._logger.appendText(f"{record.levelname}: {log_entry}\n")
        return None

    def connect_stdout(self):
        sys.stdout = self

    def disconnect_stdout(self):
        sys.stdout = sys.__stdout__

    def close(self):
        self.disconnect_logger()

    def connect_logger(self):
        default = logging.getLogger()
        for handler in default.handlers:
            default.removeHandler(handler)
        default.addHandler(self)

    def disconnect_logger(self):
        default = logging.getLogger()
        for handler in default.handlers:
            default.removeHandler(handler)
        for handler in self._default_handlers:
            default.addHandler(handler)

    @property
    def widget(self) -> QtOutputWidget:
        """Return the QLogger widget."""
        return self._widget


_INTERFACES = {}


def get_interface(id: str = "default") -> OutputInterface:
    if id in _INTERFACES:
        return _INTERFACES[id]
    interf = OutputInterface()
    interf.connect_stdout()
    interf.connect_logger()
    _INTERFACES[id] = interf
    return interf

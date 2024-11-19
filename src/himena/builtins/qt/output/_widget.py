from __future__ import annotations
import sys
from contextlib import suppress
import textwrap
import logging
from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtCore import Qt, Signal
from himena.qt._qfinderwidget import QFinderWidget
from himena.consts import MonospaceFontFamily


class QLogger(QtW.QPlainTextEdit):
    process = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setFont(QtGui.QFont(MonospaceFontFamily, 8))
        self.setReadOnly(True)
        self.setWordWrapMode(QtGui.QTextOption.WrapMode.NoWrap)
        self.process.connect(self.update_text)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self._finder_widget = None

    def update_text(self, obj: str):
        text = "\n".join(textwrap.wrap(obj, width=200))
        if obj.endswith("\n"):
            text += "\n"
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
    log_level_changed = Signal(str)

    def __init__(self):
        super().__init__()
        # stdout
        stdout_container = QtW.QWidget()
        self._stdout = QLogger()
        layout = QtW.QVBoxLayout(stdout_container)
        layout.addWidget(self._stdout)

        # logging
        logger_container = QtW.QWidget()
        self._log_level = QtW.QComboBox()
        self._log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self._log_level.setCurrentIndex(1)
        self._logger = QLogger()
        layout = QtW.QVBoxLayout(logger_container)
        layout.addWidget(self._log_level)
        layout.addWidget(self._logger)
        self._log_level.currentTextChanged.connect(self.log_level_changed.emit)

        # add tabs
        self.addTab(stdout_container, "stdout")
        self.addTab(logger_container, "log")


class OutputInterface(logging.Handler):
    _instances = {}

    def __init__(self):
        super().__init__()
        self._widget = QtOutputWidget()
        self._logger = logging.getLogger()
        self._default_handlers = self._logger.handlers.copy()
        self._logger.setLevel(logging.INFO)
        self._widget.log_level_changed.connect(self.set_log_level)

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

    def set_log_level(self, level: str):
        log_level = getattr(logging, level)
        self._logger.setLevel(log_level)
        return None

    def connect_stdout(self):
        sys.stdout = self

    def disconnect_stdout(self):
        sys.stdout = sys.__stdout__

    def close(self):
        self.disconnect_logger()

    def connect_logger(self):
        default = self._logger
        for handler in default.handlers:
            default.removeHandler(handler)
        default.addHandler(self)

    def disconnect_logger(self):
        default = self._logger
        for handler in default.handlers:
            default.removeHandler(handler)
        for handler in self._default_handlers:
            default.addHandler(handler)

    @property
    def widget(self) -> QtOutputWidget:
        """Return the QLogger widget."""
        return self._widget


def get_interface(id: str = "default") -> OutputInterface:
    if id in OutputInterface._instances:
        return OutputInterface._instances[id]
    interf = OutputInterface()
    interf.connect_stdout()
    interf.connect_logger()
    OutputInterface._instances[id] = interf
    return interf

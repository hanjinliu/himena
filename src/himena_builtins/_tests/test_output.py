from himena_builtins.qt.output._widget import get_widget
from pytestqt.qtbot import QtBot
from qtpy.QtCore import Qt
import logging


def test_stdout(qtbot: QtBot):
    widget = get_widget()._widget
    qtbot.addWidget(widget)
    assert widget._stdout.toPlainText() == ""
    print("Hello")
    assert widget._stdout.toPlainText() == "Hello\n"


def test_logger(qtbot: QtBot):
    widget = get_widget()._widget
    qtbot.addWidget(widget)
    assert widget._logger.toPlainText() == ""
    logger = logging.getLogger("test")
    logger.warning("Hello")
    assert widget._logger.toPlainText() == "Hello\n"
    qtbot.keyClick(widget._logger, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)
    widget._logger._find_string()
    widget._logger._finder_widget._line_edit.setText("Hel")
    qtbot.keyClick(widget._logger, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
    widget._log_filter.setText("himena")
    widget._log_level.setCurrentText("ERROR")
    get_widget().close()
    get_widget().disconnect_logger()
    get_widget().disconnect_stdout()

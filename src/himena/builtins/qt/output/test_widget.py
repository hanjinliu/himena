from himena.builtins.qt.output._widget import get_interface
from pytestqt.qtbot import QtBot
import logging


def test_stdout(qtbot: QtBot):
    interf = get_interface()
    widget = interf.widget
    qtbot.addWidget(widget)
    assert widget._stdout.toPlainText() == ""
    print("Hello")
    assert widget._stdout.toPlainText() == "Hello\n"


def test_logger(qtbot: QtBot):
    interf = get_interface()
    widget = interf.widget
    qtbot.addWidget(widget)
    assert widget._logger.toPlainText() == ""
    logger = logging.getLogger("test")
    logger.warning("Hello")
    assert widget._logger.toPlainText() == "WARNING: Hello\n"

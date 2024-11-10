from himena.qt._magicgui._basic_widgets import QIntLineEdit, QDoubleLineEdit
from qtpy.QtCore import Qt
from pytestqt.qtbot import QtBot

def test_int_line_edit(qtbot: QtBot):
    line = QIntLineEdit()
    qtbot.addWidget(line)
    assert line.text() == ""

    # nothing changes
    qtbot.keyClick(line, Qt.Key.Key_Up)
    qtbot.keyClick(line, Qt.Key.Key_Down)
    qtbot.keyClick(line, Qt.Key.Key_PageUp)
    qtbot.keyClick(line, Qt.Key.Key_PageDown)

    qtbot.keyClick(line, Qt.Key.Key_A)
    assert line.text() == ""  # validator
    qtbot.keyClick(line, Qt.Key.Key_5)
    assert line.text() == "5"
    qtbot.keyClick(line, Qt.Key.Key_Up)
    assert line.text() == "6"
    qtbot.keyClick(line, Qt.Key.Key_Down)
    assert line.text() == "5"
    qtbot.keyClick(line, Qt.Key.Key_PageUp)
    assert line.text() == "105"
    qtbot.keyClick(line, Qt.Key.Key_PageDown)
    assert line.text() == "5"

def test_double_line_edit(qtbot: QtBot):
    line = QDoubleLineEdit()
    qtbot.addWidget(line)
    assert line.text() == ""

    # nothing changes
    qtbot.keyClick(line, Qt.Key.Key_Up)
    qtbot.keyClick(line, Qt.Key.Key_Down)
    qtbot.keyClick(line, Qt.Key.Key_PageUp)
    qtbot.keyClick(line, Qt.Key.Key_PageDown)

    qtbot.keyClick(line, Qt.Key.Key_A)
    assert line.text() == ""  # validator
    qtbot.keyClick(line, Qt.Key.Key_3)
    qtbot.keyClick(line, Qt.Key.Key_Period)
    qtbot.keyClick(line, Qt.Key.Key_1)
    assert line.text() == "3.1"
    qtbot.keyClick(line, Qt.Key.Key_Up)
    assert line.text() == "3.2"
    qtbot.keyClick(line, Qt.Key.Key_Down)
    assert line.text() == "3.1"
    qtbot.keyClick(line, Qt.Key.Key_PageUp)
    assert line.text() == "13.1"
    qtbot.keyClick(line, Qt.Key.Key_PageDown)
    assert line.text() == "3.1"

def test_double_line_edit_exponential(qtbot: QtBot):
    line = QDoubleLineEdit()
    qtbot.addWidget(line)
    assert line.text() == ""

    qtbot.keyClick(line, Qt.Key.Key_3)
    qtbot.keyClick(line, Qt.Key.Key_Period)
    qtbot.keyClick(line, Qt.Key.Key_1)
    qtbot.keyClick(line, Qt.Key.Key_E)
    qtbot.keyClick(line, Qt.Key.Key_2)
    assert line.text() == "3.1e2"
    qtbot.keyClick(line, Qt.Key.Key_Up)
    assert line.text() == "3.2e2"
    qtbot.keyClick(line, Qt.Key.Key_Down)
    assert line.text() == "3.1e2"
    qtbot.keyClick(line, Qt.Key.Key_PageUp)
    assert line.text() == "3.1e3"
    qtbot.keyClick(line, Qt.Key.Key_PageDown)
    assert line.text() == "3.1e2"

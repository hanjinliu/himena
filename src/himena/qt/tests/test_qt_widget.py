import sys
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt
from pytestqt.qtbot import QtBot

from himena import create_model, StandardType
from himena.qt._qtraceback import QtErrorMessageBox, QtTracebackDialog
from himena.qt import MainWindowQt
from himena.qt._qmodeldrop import QModelDrop, QModelDropList

def test_qt_traceback(qtbot: QtBot):
    from himena.qt._qtraceback import format_exc_info_py310, format_exc_info_py311

    exception = ValueError("Test value error")
    widget = QtW.QWidget()
    msgbox = QtErrorMessageBox("Test", exception, parent=widget)
    qtbot.addWidget(widget)
    qtbot.addWidget(msgbox)
    tb = msgbox._get_traceback()
    tb_dlg = QtTracebackDialog(msgbox)
    qtbot.addWidget(tb_dlg)
    tb_dlg.setText(tb)

    if sys.version_info < (3, 11):
        format_exc_info_py310(msgbox._exc_info(), as_html=True)
    else:
        format_exc_info_py311(msgbox._exc_info(), as_html=True)

def test_tab_widget(qtbot: QtBot):
    from himena.qt._qtab_widget import QTabWidget

    tab_widget = QTabWidget()
    tab_widget.show()  # this is necessary for testing key click
    qtbot.addWidget(tab_widget)
    tab_widget.add_tab_area("X")
    tab_widget._line_edit.start_edit(0)
    QtW.QApplication.processEvents()
    tab_widget._line_edit.setText("Y")
    QtW.QApplication.processEvents()
    qtbot.keyClick(tab_widget._line_edit, Qt.Key.Key_Return)
    QtW.QApplication.processEvents()
    assert tab_widget.tabText(0) == "Y"

def test_int_line_edit(qtbot: QtBot):
    from himena.qt._qlineedit import QIntLineEdit

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
    from himena.qt._qlineedit import QDoubleLineEdit

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
    from himena.qt._qlineedit import QDoubleLineEdit

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

def test_int_list_line_edit(qtbot: QtBot):
    from himena.qt._qlineedit import QCommaSeparatedIntLineEdit

    line = QCommaSeparatedIntLineEdit()
    qtbot.addWidget(line)
    assert line.text() == ""

    qtbot.keyClick(line, Qt.Key.Key_1)
    qtbot.keyClick(line, Qt.Key.Key_Comma)
    assert line.text() == "1,"
    qtbot.keyClick(line, Qt.Key.Key_2)
    qtbot.keyClick(line, Qt.Key.Key_Comma)
    qtbot.keyClick(line, Qt.Key.Key_Space)
    qtbot.keyClick(line, Qt.Key.Key_3)
    assert line.text() == "1,2, 3"
    qtbot.keyClick(line, Qt.Key.Key_Comma)
    qtbot.keyClick(line, Qt.Key.Key_Comma)
    assert line.text() == "1,2, 3,"

def test_float_list_line_edit(qtbot: QtBot):
    from himena.qt._qlineedit import QCommaSeparatedDoubleLineEdit

    line = QCommaSeparatedDoubleLineEdit()
    qtbot.addWidget(line)
    assert line.text() == ""

    qtbot.keyClick(line, Qt.Key.Key_1)
    qtbot.keyClick(line, Qt.Key.Key_Comma)
    assert line.text() == "1,"
    qtbot.keyClick(line, Qt.Key.Key_2)
    qtbot.keyClick(line, Qt.Key.Key_Comma)
    qtbot.keyClick(line, Qt.Key.Key_Space)
    qtbot.keyClick(line, Qt.Key.Key_3)
    assert line.text() == "1,2, 3"
    qtbot.keyClick(line, Qt.Key.Key_Comma)
    qtbot.keyClick(line, Qt.Key.Key_Comma)
    assert line.text() == "1,2, 3,"

def test_int_line_edit_range(qtbot: QtBot):
    from himena.qt._qlineedit import QIntLineEdit

    line = QIntLineEdit()
    qtbot.addWidget(line)
    line.setMinimum(10)
    line.setMaximum(100)
    line.setText("10")
    assert line.text() == "10"
    line.stepUp()
    assert line.text() == "11"
    line.stepDown()
    assert line.text() == "10"
    line.stepDown()
    assert line.text() == "10"
    # check upper limit
    line.setText("100")
    line.stepDown()
    assert line.text() == "99"
    line.stepUp()
    assert line.text() == "100"
    line.stepUp()
    assert line.text() == "100"

def test_float_line_edit_range(qtbot: QtBot):
    from himena.qt._qlineedit import QDoubleLineEdit

    line = QDoubleLineEdit()
    qtbot.addWidget(line)

    line = QDoubleLineEdit()
    qtbot.addWidget(line)
    line.setMinimum(0.0)
    line.setMaximum(1.0)
    line.setText("0.0")
    assert line.text() == "0.0"
    line.stepUp()
    assert line.text() == "0.1"
    line.stepDown()
    assert line.text() == "0.0"
    line.stepDown()
    assert line.text() == "0.0"
    # check upper limit
    line.setText("1.0")
    line.stepDown()
    assert line.text() == "0.9"
    line.stepUp()
    assert line.text() == "1.0"
    line.stepUp()
    assert line.text() == "1.0"

def test_model_drop(himena_ui: MainWindowQt):
    himena_ui.add_object("abc", type=StandardType.TEXT)
    himena_ui.add_object([[0, 1], [2, 3]], type="table")
    qdrop = QModelDrop([StandardType.TEXT])
    qdroplist = QModelDropList([StandardType.TEXT])
    drop_win = himena_ui.add_widget(qdrop)
    drop_list = himena_ui.add_widget(qdroplist)
    qwins = himena_ui._backend_main_window._tab_widget.widget_area(0).subWindowList()
    qdrop._drop_qsubwindow(qwins[0])
    assert qdrop.to_model().value == "abc"
    assert qdrop.to_model().type == StandardType.TEXT
    qdrop._drop_qsubwindow(qwins[1])
    assert qdrop.to_model().value == "abc"  # type not accepted, so not changed
    assert qdrop.to_model().type == StandardType.TEXT
    qdrop.set_model(create_model("pqr", type=StandardType.TEXT))
    assert qdrop.to_model().value == "pqr"
    qdroplist._drop_qsubwindow(qwins[0])
    qdroplist._drop_qsubwindow(qwins[1])
    assert len(qdroplist.models()) == 1
    assert qdroplist.models()[0].type == StandardType.TEXT
    qdroplist.itemWidget(qdroplist.item(0))._update_btn_pos()
    qdroplist.set_models(None)

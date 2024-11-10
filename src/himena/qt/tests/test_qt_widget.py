import sys
from himena.qt._qtraceback import QtErrorMessageBox, QtTracebackDialog
from qtpy.QtCore import Qt
from pytestqt.qtbot import QtBot

def test_qt_traceback(qtbot: QtBot):
    from himena.qt._qtraceback import format_exc_info_py310, format_exc_info_py311

    exception = ValueError("Test value error")
    msgbox = QtErrorMessageBox("Test", exception, parent=None)
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
    tab_widget.show()
    qtbot.addWidget(tab_widget)
    tab_widget.add_tab_area("X")
    tab_widget._start_editing_tab(0)
    tab_widget._line_edit.setText("Y")
    qtbot.keyClick(tab_widget._line_edit, Qt.Key.Key_Return)
    assert tab_widget.tabText(0) == "Y"

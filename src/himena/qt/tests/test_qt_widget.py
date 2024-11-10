from himena.qt._qtraceback import QtErrorMessageBox, QtTracebackDialog
from pytestqt.qtbot import QtBot

def test_qt_traceback(qtbot: QtBot):
    exception = ValueError("Test value error")
    msgbox = QtErrorMessageBox("Test", exception, parent=None)
    qtbot.addWidget(msgbox)
    tb = msgbox._get_traceback()
    tb_dlg = QtTracebackDialog(msgbox)
    qtbot.addWidget(tb_dlg)
    tb_dlg.setText(tb)

def test_tab_widget(qtbot: QtBot):
    from himena.qt._qtab_widget import QTabWidget

    tab_widget = QTabWidget()
    tab_widget.show()
    qtbot.addWidget(tab_widget)
    tab_widget.add_tab_area("X")
    tab_widget._start_editing_tab(0)
    tab_widget._line_edit.setText("Y")
    tab_widget.setFocus()
    assert tab_widget.tabText(0) == "Y"

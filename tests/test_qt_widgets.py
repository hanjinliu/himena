from qtpy import QtCore, QtWidgets as QtW, QtGui
from himena import MainWindow
from himena.qt._qmain_window import QMainWindow
from himena.qt._qsub_window import QSubWindow, QSubWindowTitleBar
from pytestqt.qtbot import QtBot

def test_subwindow_interactions(ui: MainWindow, qtbot: QtBot):
    ui.show()
    qmain: QMainWindow = ui._backend_main_window
    qtbot.addWidget(qmain)

    win = ui.add_data("xxx", type="text")
    qwin = win.widget.parentWidget().parentWidget().parentWidget()
    assert type(qwin) is QSubWindow
    qtitlebar: QSubWindowTitleBar = qwin._title_bar

    qtbot.mouseClick(
        qtitlebar._minimize_btn,
        QtCore.Qt.MouseButton.LeftButton,
        pos=qtitlebar._minimize_btn.rect().center(),
    )
    qtbot.mouseClick(
        qtitlebar._toggle_size_btn,
        QtCore.Qt.MouseButton.LeftButton,
        pos=qtitlebar._toggle_size_btn.rect().center(),
    )
    qtbot.mouseClick(
        qtitlebar._close_btn,
        QtCore.Qt.MouseButton.LeftButton,
        pos=qtitlebar._close_btn.rect().center(),
    )

    win = ui.add_data("xxx", type="text")
    qwin = win.widget.parentWidget().parentWidget().parentWidget()
    assert type(qwin) is QSubWindow
    qtitlebar: QSubWindowTitleBar = qwin._title_bar
    qtbot.mouseDClick(
        qtitlebar,
        QtCore.Qt.MouseButton.LeftButton,
        pos=qtitlebar.rect().center(),
    )

def test_subwindow_drag(ui: MainWindow, qtbot: QtBot):
    ui.show()
    qmain: QMainWindow = ui._backend_main_window
    qtbot.addWidget(qmain)

    win = ui.add_data("xxx", type="text")
    qwin = win.widget.parentWidget().parentWidget().parentWidget()
    assert type(qwin) is QSubWindow

    point = qwin.rect().bottomRight()

    qtbot.mouseMove(
        qwin,
        pos=point - QtCore.QPoint(2, 2),
    )
    qtbot.mousePress(
        qmain,
        QtCore.Qt.MouseButton.LeftButton,
        pos=point - QtCore.QPoint(2, 2),
    )
    qtbot.mouseMove(
        qmain,
        pos=point + QtCore.QPoint(15, 15)
    )
    qtbot.mouseRelease(
        qmain,
        QtCore.Qt.MouseButton.LeftButton,
        pos=point + QtCore.QPoint(15, 15),
    )

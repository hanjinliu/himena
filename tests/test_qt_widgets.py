import sys
from qtpy import QtCore
from himena import MainWindow
from himena.qt._qmain_window import QMainWindow
from himena.qt._qsub_window import QSubWindow, QSubWindowTitleBar
from pytestqt.qtbot import QtBot

def test_subwindow_interactions(himena_ui: MainWindow, qtbot: QtBot):
    himena_ui.show()
    qmain: QMainWindow = himena_ui._backend_main_window
    qtbot.addWidget(qmain)

    win = himena_ui.add_object("xxx", type="text")
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

    win = himena_ui.add_object("xxx", type="text")
    qwin = win.widget.parentWidget().parentWidget().parentWidget()
    assert type(qwin) is QSubWindow
    qtitlebar: QSubWindowTitleBar = qwin._title_bar
    qtbot.mouseDClick(
        qtitlebar,
        QtCore.Qt.MouseButton.LeftButton,
        pos=qtitlebar.rect().center(),
    )

    qwin._title_bar._make_tooltip()
    qwin._title_bar._prep_model_menu()
    qwin._title_bar._prep_window_menu()
    qwin._title_bar._wheel_event(1)
    qwin._title_bar._wheel_event(-1)

def test_subwindow_drag(himena_ui: MainWindow, qtbot: QtBot):
    himena_ui.show()
    win = himena_ui.add_object("xxx", type="text")
    qwin = win.widget.parentWidget().parentWidget().parentWidget()
    assert type(qwin) is QSubWindow
    qtbot.addWidget(qwin)
    qtitlebar: QSubWindowTitleBar = qwin._title_bar
    point = qwin.rect().bottomRight()

    qtbot.mousePress(
        qwin,
        QtCore.Qt.MouseButton.LeftButton,
        pos=point - QtCore.QPoint(2, 2),
        delay=10,
    )
    qtbot.mouseMove(
        qwin,
        pos=point + QtCore.QPoint(1, 1),
        delay=10,
    )
    qtbot.mouseRelease(
        qwin,
        QtCore.Qt.MouseButton.LeftButton,
        pos=point + QtCore.QPoint(1, 1),
        delay=10,
    )

    qtbot.mousePress(
        qtitlebar,
        QtCore.Qt.MouseButton.LeftButton,
        pos=qtitlebar.rect().center(),
        delay=10,
    )
    qtbot.mouseMove(
        qtitlebar,
        pos=qtitlebar.rect().center() + QtCore.QPoint(12, 0),
        delay=10,
    )
    qtbot.mouseRelease(
        qtitlebar,
        QtCore.Qt.MouseButton.LeftButton,
        pos=qtitlebar.rect().center() + QtCore.QPoint(12, 0),
        delay=10,
    )

    if sys.platform == "ubuntu":
        return
    ## FIXME: ubuntu gets stuck here
    qtbot.mousePress(
        qtitlebar,
        QtCore.Qt.MouseButton.LeftButton,
        modifier=QtCore.Qt.KeyboardModifier.ControlModifier,
        pos=qtitlebar.rect().center(),
        delay=10,
    )
    qtbot.mouseMove(
        qtitlebar,
        pos=qtitlebar.rect().center() + QtCore.QPoint(12, 0),
        delay=10,
    )
    qtbot.mouseRelease(
        qtitlebar,
        QtCore.Qt.MouseButton.LeftButton,
        modifier=QtCore.Qt.KeyboardModifier.ControlModifier,
        pos=qtitlebar.rect().center() + QtCore.QPoint(12, 0),
        delay=10,
    )

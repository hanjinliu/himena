from himena import MainWindow, anchor
from himena.qt import MainWindowQt
from himena.qt._qmain_window import QMainWindow
from himena_builtins.qt import widgets as _qtw
from qtpy.QtCore import Qt
from pathlib import Path
from pytestqt.qtbot import QtBot

from himena.types import WidgetDataModel, WindowRect

def test_type_map_and_session(tmpdir, ui: MainWindow, sample_dir):
    tab0 = ui.add_tab()
    tab0.read_file(sample_dir / "text.txt").update(rect=(30, 40, 120, 150))
    assert type(tab0.current().widget) is _qtw.QTextEdit
    tab0.read_file(sample_dir / "json.json").update(rect=(150, 40, 250, 150), anchor="top-left")
    assert type(tab0.current().widget) is _qtw.QTextEdit
    tab1 = ui.add_tab()
    tab1.read_file(sample_dir / "image.png").update(rect=(30, 40, 160, 130), title="My Image")
    assert type(tab1.current().widget) is _qtw.QImageView
    tab1.read_file(sample_dir / "html.html").update(rect=(80, 40, 160, 130), title="My HTML")
    # assert type(tab1.current().widget) is _qtw.QDefaultHTMLEdit ?

    session_path = Path(tmpdir) / "test.session.json"
    ui.save_session(session_path)
    ui.clear()
    assert len(ui.tabs) == 0
    ui.read_session(session_path)
    assert len(ui.tabs) == 2
    assert len(ui.tabs[0]) == 2
    assert ui.tabs[0][0].title == "text.txt"
    assert ui.tabs[0][0].rect == WindowRect(30, 40, 120, 150)
    assert ui.tabs[0][1].title == "json.json"
    assert ui.tabs[0][1].rect == WindowRect(150, 40, 250, 150)
    assert isinstance(ui.tabs[0][1].anchor, anchor.TopLeftConstAnchor)
    assert len(ui.tabs[1]) == 2
    assert ui.tabs[1][0].title == "My Image"
    assert ui.tabs[1][0].rect == WindowRect(30, 40, 160, 130)
    assert ui.tabs[1][1].title == "My HTML"
    assert ui.tabs[1][1].rect == WindowRect(80, 40, 160, 130)

def test_command_palette_events(ui: MainWindowQt, qtbot: QtBot):
    ui.show()
    ui.exec_action("show-command-palette")
    qmain: QMainWindow = ui._backend_main_window
    qtbot.add_widget(qmain)
    qline = qmain._command_palette_general._line
    qtbot.keyClick(qline, Qt.Key.Key_O)
    qtbot.keyClick(qline, Qt.Key.Key_Down)
    qtbot.keyClick(qline, Qt.Key.Key_PageDown)
    qtbot.keyClick(qline, Qt.Key.Key_Up)
    qtbot.keyClick(qline, Qt.Key.Key_PageUp)
    qtbot.keyClick(qline, Qt.Key.Key_Escape)

def test_goto_widget(ui: MainWindowQt, qtbot: QtBot):
    ui.show()
    tab0 = ui.add_tab(title="Tab 0")
    tab0.add_data_model(WidgetDataModel(value="a", type="text", title="A"))
    tab0.add_data_model(WidgetDataModel(value="b", type="text", title="B"))
    tab1 = ui.add_tab(title="Tab 1")
    tab1.add_data_model(WidgetDataModel(value="c", type="text", title="C"))
    tab1.add_data_model(WidgetDataModel(value="d", type="text", title="D"))
    tab1.add_data_model(WidgetDataModel(value="e", type="text", title="E"))

    ui.exec_action("go-to-window")
    qmain: QMainWindow = ui._backend_main_window
    qmain._goto_widget.show()
    qtbot.keyClick(qmain._goto_widget, Qt.Key.Key_Down)
    qtbot.keyClick(qmain._goto_widget, Qt.Key.Key_Up)
    qtbot.keyClick(qmain._goto_widget, Qt.Key.Key_Right)
    qtbot.keyClick(qmain._goto_widget, Qt.Key.Key_Left)
    qtbot.keyClick(qmain._goto_widget, Qt.Key.Key_Down)
    qtbot.keyClick(qmain._goto_widget, Qt.Key.Key_Return)
    ui.exec_action("go-to-window")
    qtbot.keyClick(qmain._goto_widget, Qt.Key.Key_Escape)

def test_register_function_in_runtime(ui: MainWindowQt, qtbot: QtBot):
    qmain: QMainWindow = ui._backend_main_window
    assert qmain._menubar.actions()[-2].menu().title() != "Plugins"

    @ui.register_function(menus="plugins", title="F0", command_id="pytest:f0")
    def f():
        pass

    assert qmain._menubar.actions()[-2].menu().title() == "Plugins"
    assert qmain._menubar.actions()[-2].menu().actions()[0].text() == "F0"

    @ui.register_function(menus="tools", title="F1", command_id="pytest:f1")
    def f():
        pass

    assert qmain._menubar.actions()[-2].menu().title() == "Plugins"
    titles = [a.text() for a in qmain._get_menu_action_by_id("tools").menu().actions()]
    assert "F1" in titles

    @ui.register_function(menus="plugins2/sub", title="F2", command_id="pytest:f2")
    def f():
        pass

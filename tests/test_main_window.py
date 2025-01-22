import warnings
from himena import MainWindow, anchor
from himena.consts import StandardType
from himena.qt import MainWindowQt
from himena.qt._qmain_window import QMainWindow
from himena.standards.model_meta import DataFrameMeta
from himena.widgets import set_status_tip, notify
from himena_builtins.qt import widgets as _qtw

from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt, QPoint
from pathlib import Path
from pytestqt.qtbot import QtBot

from himena.types import WidgetDataModel, WindowRect

def test_type_map_and_session(tmpdir, himena_ui: MainWindow, sample_dir):
    tab0 = himena_ui.add_tab()
    tab0.read_file(sample_dir / "text.txt").update(rect=(30, 40, 120, 150))
    assert type(tab0.current().widget) is _qtw.QTextEdit
    tab0.read_file(sample_dir / "json.json").update(rect=(150, 40, 250, 150), anchor="top-left")
    assert type(tab0.current().widget) is _qtw.QTextEdit
    tab1 = himena_ui.add_tab()
    tab1.read_file(sample_dir / "image.png").update(rect=(30, 40, 160, 130), title="My Image")
    assert type(tab1.current().widget) is _qtw.QImageView
    tab1.read_file(sample_dir / "html.html").update(rect=(80, 40, 160, 130), title="My HTML")
    # assert type(tab1.current().widget) is _qtw.QDefaultHTMLEdit ?

    himena_ui.exec_action("show-whats-this")
    session_path = Path(tmpdir) / "test.session.zip"
    himena_ui.save_session(session_path)
    himena_ui.clear()
    assert len(himena_ui.tabs) == 0
    himena_ui.load_session(session_path)
    assert len(himena_ui.tabs) == 2
    assert len(himena_ui.tabs[0]) == 2
    assert himena_ui.tabs[0][0].title == "text.txt"
    assert himena_ui.tabs[0][0].rect == WindowRect(30, 40, 120, 150)
    assert himena_ui.tabs[0][1].title == "json.json"
    assert himena_ui.tabs[0][1].rect == WindowRect(150, 40, 250, 150)
    assert isinstance(himena_ui.tabs[0][1].anchor, anchor.TopLeftConstAnchor)
    assert len(himena_ui.tabs[1]) == 2
    assert himena_ui.tabs[1][0].title == "My Image"
    assert himena_ui.tabs[1][0].rect == WindowRect(30, 40, 160, 130)
    assert himena_ui.tabs[1][1].title == "My HTML"
    assert himena_ui.tabs[1][1].rect == WindowRect(80, 40, 160, 130)

def test_session_with_calculation(tmpdir, himena_ui: MainWindow, sample_dir):
    tab0 = himena_ui.add_tab()
    tab0.read_file(sample_dir / "image.png").update(rect=(30, 40, 160, 130), title="Im")
    himena_ui.exec_action("builtins:image-crop:crop-image", with_params={"y": (1, 3), "x": (1, 3)})
    assert len(tab0) == 2
    shape_cropped = tab0[1].to_model().value.shape
    tab0[1].update(rect=(70, 20, 160, 130))
    session_path = Path(tmpdir) / "test.session.zip"
    himena_ui.save_session(session_path, allow_calculate=["builtins:image-crop:crop-image"])
    himena_ui.clear()
    himena_ui.load_session(session_path)
    tab0 = himena_ui.tabs[0]
    assert len(tab0) == 2
    assert tab0[0].title == "Im"
    assert tab0[0].rect == WindowRect(30, 40, 160, 130)
    assert tab0[1].rect == WindowRect(70, 20, 160, 130)
    assert tab0[1].to_model().value.shape == shape_cropped

def test_session_stand_alone(tmpdir, himena_ui: MainWindow, sample_dir):
    tab0 = himena_ui.add_tab()
    tab0.read_file(sample_dir / "image.png").update(rect=(30, 40, 160, 130), title="Im")
    himena_ui.exec_action("builtins:image-crop:crop-image", with_params={"y": (1, 3), "x": (1, 3)})
    shape_cropped = tab0[1].to_model().value.shape
    tab0[1].update(rect=(70, 20, 160, 130))

    tab1 = himena_ui.add_tab()
    tab1.read_file(sample_dir / "text.txt")
    win = tab1.read_file(
        sample_dir / "table.csv",
        plugin="himena_builtins.io.read_as_pandas_dataframe",
    )
    assert isinstance(win.widget, _qtw.QDataFrameView)
    win.widget.selection_model.set_ranges([(slice(1, 3), slice(1, 2))])
    session_path = Path(tmpdir) / "test.session.zip"
    himena_ui.save_session(session_path, save_copies=True)
    himena_ui.clear()
    himena_ui.load_session(session_path)
    tab0 = himena_ui.tabs[0]
    tab1 = himena_ui.tabs[1]
    assert len(tab0) == 2
    assert tab0[0].title == "Im"
    assert tab0[0].rect == WindowRect(30, 40, 160, 130)
    assert tab0[1].rect == WindowRect(70, 20, 160, 130)
    assert tab0[1].to_model().value.shape == shape_cropped
    assert tab1[1].model_type() == StandardType.DATAFRAME
    assert isinstance(meta := tab1[1].to_model().metadata, DataFrameMeta)
    assert meta.selections == [((1, 3), (1, 2))]

def test_command_palette_events(himena_ui: MainWindowQt, qtbot: QtBot):
    himena_ui.show()
    himena_ui.exec_action("show-command-palette")
    qmain: QMainWindow = himena_ui._backend_main_window
    qtbot.add_widget(qmain)
    qline = qmain._command_palette_general._line
    qtbot.keyClick(qline, Qt.Key.Key_O)
    qtbot.keyClick(qline, Qt.Key.Key_Down)
    qtbot.keyClick(qline, Qt.Key.Key_PageDown)
    qtbot.keyClick(qline, Qt.Key.Key_Up)
    qtbot.keyClick(qline, Qt.Key.Key_PageUp)
    qtbot.keyClick(qline, Qt.Key.Key_Escape)

def test_goto_widget(himena_ui: MainWindowQt, qtbot: QtBot):
    himena_ui.show()
    tab0 = himena_ui.add_tab(title="Tab 0")
    tab0.add_data_model(WidgetDataModel(value="a", type="text", title="A"))
    tab0.add_data_model(WidgetDataModel(value="b", type="text", title="B"))
    tab1 = himena_ui.add_tab(title="Tab 1")
    tab1.add_data_model(WidgetDataModel(value="c", type="text", title="C"))
    tab1.add_data_model(WidgetDataModel(value="d", type="text", title="D"))
    tab1.add_data_model(WidgetDataModel(value="e", type="text", title="E"))

    himena_ui.exec_action("go-to-window")
    qmain: QMainWindow = himena_ui._backend_main_window
    qmain._goto_widget.show()
    qtbot.keyClick(qmain._goto_widget, Qt.Key.Key_Down)
    qtbot.keyClick(qmain._goto_widget, Qt.Key.Key_Up)
    qtbot.keyClick(qmain._goto_widget, Qt.Key.Key_Right)
    qtbot.keyClick(qmain._goto_widget, Qt.Key.Key_Left)
    qtbot.keyClick(qmain._goto_widget, Qt.Key.Key_Down)
    qtbot.keyClick(qmain._goto_widget, Qt.Key.Key_Return)
    himena_ui.exec_action("go-to-window")
    qtbot.keyClick(qmain._goto_widget, Qt.Key.Key_Escape)

def test_register_function_in_runtime(himena_ui: MainWindowQt, qtbot: QtBot):
    qmain = himena_ui._backend_main_window
    assert qmain._menubar.actions()[-2].menu().title() != "Plugins"

    @himena_ui.register_function(menus="plugins", title="F0", command_id="pytest:f0")
    def f():
        pass

    assert qmain._menubar.actions()[-2].menu().title() == "Plugins"
    assert qmain._menubar.actions()[-2].menu().actions()[0].text() == "F0"

    @himena_ui.register_function(menus="tools", title="F1", command_id="pytest:f1")
    def f():
        pass

    assert qmain._menubar.actions()[-2].menu().title() == "Plugins"
    titles = [a.text() for a in qmain._get_menu_action_by_id("tools").menu().actions()]
    assert "F1" in titles

    @himena_ui.register_function(menus="plugins2/sub", title="F2", command_id="pytest:f2")
    def f():
        pass

def test_notification_and_status_tip(himena_ui: MainWindowQt):
    set_status_tip("my text", duration=0.1)
    notify("my text", duration=0.1)
    himena_ui._backend_main_window._on_error(ValueError("error msg"))
    himena_ui._backend_main_window._on_error(ValueError())
    himena_ui._backend_main_window._on_error(ValueError("msg 1", "msg 2"))
    himena_ui._backend_main_window._on_warning(warnings.WarningMessage("msg", UserWarning, "file", 1))

def test_dock_widget(himena_ui: MainWindow):
    assert len(himena_ui.dock_widgets) == 0
    widget = _qtw.QTextEdit()
    dock = himena_ui.add_dock_widget(widget)
    assert len(himena_ui.dock_widgets) == 1
    dock.hide()
    dock.show()
    dock.title = "new title"
    assert dock.title == "new title"
    del himena_ui.dock_widgets[0]
    assert len(himena_ui.dock_widgets) == 0

def test_setting_widget(himena_ui: MainWindow, qtbot: QtBot):
    from himena.qt.settings import QSettingsDialog

    dlg = QSettingsDialog(himena_ui)
    qtbot.addWidget(dlg)

def test_mouse_events(himena_ui: MainWindowQt, qtbot: QtBot):
    tab = himena_ui.add_tab()
    win = tab.add_widget(_qtw.QTextEdit())
    qmain = himena_ui._backend_main_window
    qarea = qmain._tab_widget.widget_area(0)
    assert qarea is not None
    qtbot.mouseClick(qarea, Qt.MouseButton.LeftButton)
    qtbot.mouseMove(qarea, qarea.rect().center())
    qtbot.mouseMove(qarea, qarea.rect().center() + QPoint(10, 10))
    qtbot.mousePress(qarea, Qt.MouseButton.LeftButton)
    qtbot.mouseMove(qarea, qarea.rect().center())
    qtbot.mouseMove(qarea, qarea.rect().center() + QPoint(10, 10))
    qtbot.mouseRelease(qarea, Qt.MouseButton.LeftButton)
    qtbot.mousePress(qarea, Qt.MouseButton.RightButton)
    qtbot.mouseMove(qarea, qarea.rect().center())
    qtbot.mouseMove(qarea, qarea.rect().center() + QPoint(10, 10))
    qtbot.mouseRelease(qarea, Qt.MouseButton.RightButton)
    qmain._tab_widget.tabBar().tabButton(0, QtW.QTabBar.ButtonPosition.RightSide).click()

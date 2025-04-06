import warnings

import numpy as np
import pytest
from himena import MainWindow
from himena.qt import MainWindowQt
from himena.qt._qmain_window import QMainWindow
from himena.widgets import set_status_tip, notify, append_result
from himena_builtins.qt.text import QTextEdit

from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt, QPoint
from pytestqt.qtbot import QtBot

from himena.types import WidgetDataModel

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
    himena_ui.show()
    set_status_tip("my text", duration=0.1)
    notify("my text", duration=0.1)
    himena_ui._backend_main_window._on_error(ValueError("error msg"))
    himena_ui._backend_main_window._on_error(ValueError())
    himena_ui._backend_main_window._on_error(ValueError("msg 1", "msg 2"))
    himena_ui._backend_main_window._on_warning(warnings.WarningMessage("msg", UserWarning, "file", 1))

def test_dock_widget(himena_ui: MainWindow):
    assert len(himena_ui.dock_widgets) == 0
    widget = QTextEdit()
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
    win = tab.add_widget(QTextEdit())
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

def test_layout_commands(himena_ui: MainWindowQt, qtbot: QtBot):
    tab0 = himena_ui.add_tab()
    win0 = tab0.add_widget(QTextEdit())
    win1 = tab0.add_widget(QTextEdit())
    himena_ui.exec_action("window-layout-horizontal", with_params={"wins": [win0, win1]})
    tab1 = himena_ui.add_tab()
    win0 = tab0.add_widget(QTextEdit())
    win1 = tab0.add_widget(QTextEdit())
    himena_ui.exec_action("window-layout-vertical", with_params={"wins": [win0, win1]})

def test_profile():
    from himena import profile

    profile.new_app_profile("abc")
    with pytest.raises(ValueError):
        profile.new_app_profile("abc")

    profile.iter_app_profiles()
    profile.remove_app_profile("abc")

def test_setting_dialog_contents(himena_ui: MainWindowQt, qtbot: QtBot):
    from himena.qt.settings._plugins import QPluginListEditor
    from himena.qt.settings._startup_commands import QStartupCommandsPanel
    from himena.qt.settings._keybind_edit import QKeybindEdit
    from himena.qt.settings._theme import QThemePanel

    editor = QPluginListEditor(himena_ui)
    qtbot.addWidget(editor)
    editor._apply_changes()

    startup = QStartupCommandsPanel(himena_ui)
    startup._apply_changes()
    startup._on_text_changed()

    theme_panel = QThemePanel(himena_ui)
    qtbot.addWidget(theme_panel)
    theme_panel.setTheme("light-blue")

    keybind_edit = QKeybindEdit(himena_ui)
    qtbot.addWidget(keybind_edit)
    keybind_edit._search.setText("A")
    keybind_edit._search.setText("")
    keybind_edit._table.setCurrentCell(0, 1)
    keybind_edit._table.edit(keybind_edit._table.currentIndex())
    keybind_edit._on_keybinding_updated("builtins:seaborn-sample:iris", "Ctrl+Alt+K")
    keybind_edit._table._update_keybinding(0, 1)
    keybind_edit._restore_default_btn.click()

def test_notification(himena_ui: MainWindowQt):
    from himena.qt._qnotification import QNotificationWidget

    notif = QNotificationWidget(himena_ui._backend_main_window, duration=0)
    notif.show()
    notif._enter_event()
    notif._leave_event()
    notif.hide()

def test_result_stack(himena_ui: MainWindowQt, qtbot: QtBot):
    from himena.qt._qresult_stack import QResultStack

    assert len(himena_ui.tabs) == 0
    append_result({"a": 10, "b": np.arange(3)})
    assert len(himena_ui.tabs) == 1
    assert len(himena_ui.tabs[0]) == 1
    assert (rstack := himena_ui.tabs[0]._result_stack_ref()) is not None
    assert isinstance(rstack, QResultStack)
    append_result({"a": 4, "b": 5})
    append_result({"a": 2, "c": 6})
    rstack.selectRow(0)
    rstack._select_rows_with_same_keys()
    assert rstack.selections() == [0, 1]
    rstack._make_context_menu()
    rstack._copy_items([0, 1])
    win = himena_ui.current_window
    himena_ui.exec_action("builtins:results:results-to-table", window_context=win)
    himena_ui.exec_action("builtins:results:selected-results-to-table", window_context=win)

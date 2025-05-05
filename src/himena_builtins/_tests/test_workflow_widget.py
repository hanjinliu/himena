from qtpy.QtWidgets import QApplication
from pytestqt.qtbot import QtBot
from himena import MainWindow
from himena.testing import WidgetTester
from himena_builtins.qt.basic import QWorkflowView
from himena_builtins._io import default_workflow_reader
from qtpy.QtCore import Qt
from pathlib import Path

_Ctrl = Qt.KeyboardModifier.ControlModifier

def test_workflow_view(qtbot: QtBot, sample_dir: Path):
    widget = QWorkflowView()
    widget.show()
    qtbot.addWidget(widget)
    with WidgetTester(widget) as tester:
        tester.update_model(default_workflow_reader(sample_dir / "test.workflow.json"))
        tester.cycle_model()
        QApplication.processEvents()
        vp = widget._tree_widget.viewport()
        qtbot.keyClick(vp, Qt.Key.Key_Down)
        qtbot.keyClick(vp, Qt.Key.Key_Up)
        qtbot.keyClick(vp, Qt.Key.Key_Down, _Ctrl)
        qtbot.keyClick(vp, Qt.Key.Key_Up, _Ctrl)
        widget._tree_widget.update()
        widget._make_context_menu(widget._tree_widget.topLevelItem(0))
        pos = widget._tree_widget.visualItemRect(widget._tree_widget.topLevelItem(0)).center()
        widget._tree_widget._make_drag(pos)

def test_edit_workflow_view(qtbot: QtBot, sample_dir: Path):
    widget = QWorkflowView()
    widget.show()
    qtbot.addWidget(widget)
    with WidgetTester(widget) as tester:
        tester.update_model(default_workflow_reader(sample_dir / "test.workflow.json"))
        widget._toggle_to_be_added(widget._tree_widget.topLevelItem(0))
        widget._replace_with_file_reader(widget._tree_widget.topLevelItem(0), "file")
        widget._replace_with_file_reader(widget._tree_widget.topLevelItem(0), "model")

def test_find_window(himena_ui: MainWindow):
    win0 = himena_ui.add_object("a")
    himena_ui.exec_action("duplicate-window")
    himena_ui.exec_action("show-workflow-graph")
    win1 = himena_ui.current_window
    assert isinstance(win1.widget, QWorkflowView)
    win1.widget._find_window(win1.widget._tree_widget.topLevelItem(0))
    assert himena_ui.current_window is win0

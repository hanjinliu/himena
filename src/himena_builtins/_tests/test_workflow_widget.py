from qtpy.QtWidgets import QApplication
from pytestqt.qtbot import QtBot
from himena import MainWindow
from himena.testing import WidgetTester
from himena_builtins.qt.basic import QWorkflowView
from himena_builtins._io import default_workflow_reader
from pathlib import Path


def test_workflow_view(qtbot: QtBot, sample_dir: Path):
    widget = QWorkflowView()
    widget.show()
    qtbot.addWidget(widget)
    with WidgetTester(widget) as tester:
        tester.update_model(default_workflow_reader(sample_dir / "test.workflow.json"))
        tester.cycle_model()
        QApplication.processEvents()
        item0 = widget.view.item(widget.view.list_ids()[0])
        assert item0 is not None
        widget._make_context_menu(item0)

def test_edit_workflow_view(qtbot: QtBot, sample_dir: Path):
    widget = QWorkflowView()
    widget.show()
    qtbot.addWidget(widget)
    with WidgetTester(widget) as tester:
        tester.update_model(default_workflow_reader(sample_dir / "test.workflow.json"))
        item0 = widget.view.item(widget.view.list_ids()[0])
        assert item0 is not None
        widget._toggle_to_be_added(item0)
        widget._replace_with_file_reader(item0, "file")
        widget._replace_with_file_reader(item0, "model")

def test_find_window(himena_ui: MainWindow):
    win0 = himena_ui.add_object("a")
    himena_ui.exec_action("duplicate-window")
    himena_ui.exec_action("show-workflow-graph")
    win1 = himena_ui.current_window
    assert isinstance(win1.widget, QWorkflowView)
    item0 = win1.widget.view.item(win1.widget.view.list_ids()[0])
    assert item0 is not None
    win1.widget._find_window(item0)
    assert himena_ui.current_window is win0

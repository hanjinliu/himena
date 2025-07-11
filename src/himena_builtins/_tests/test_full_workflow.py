from qtpy.QtWidgets import QApplication
from pytestqt.qtbot import QtBot
from himena import MainWindow
from himena_builtins.qt.full_workflow._widget import QFullWorkflowView

def _mock_single_shot(ms, slot):
    """Mock single shot to avoid timing issues in tests."""
    slot()

def test_full_workflow_widget(qtbot: QtBot, himena_ui: MainWindow):
    widget = QFullWorkflowView(himena_ui)
    widget._single_shot = _mock_single_shot
    himena_ui.add_dock_widget(widget)
    himena_ui.add_object("abc,d")
    himena_ui.exec_action("builtins:text:change-separator", with_params={})
    assert len(widget.view.list_ids()) == 2
    himena_ui.tabs[0].pop(1)
    QApplication.processEvents()
    assert len(widget.view.list_ids()) == 1

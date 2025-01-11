from pytestqt.qtbot import QtBot
from himena.testing import WidgetTester
from himena_builtins.qt.widgets import QWorkflowView
from himena_builtins._io import default_workflow_reader
from qtpy.QtCore import Qt
from pathlib import Path

_Ctrl = Qt.KeyboardModifier.ControlModifier

def test_workflow_view(qtbot: QtBot, sample_dir: Path):
    widget = QWorkflowView()
    qtbot.addWidget(widget)
    widget.show()
    with WidgetTester(widget) as tester:
        tester.update_model(default_workflow_reader(sample_dir / "test.workflow.json"))
        tester.cycle_model()
        qtbot.keyClick(tester.widget, Qt.Key.Key_Down)
        qtbot.keyClick(tester.widget, Qt.Key.Key_Up)
        qtbot.keyClick(tester.widget, Qt.Key.Key_Down, _Ctrl)
        qtbot.keyClick(tester.widget, Qt.Key.Key_Up, _Ctrl)

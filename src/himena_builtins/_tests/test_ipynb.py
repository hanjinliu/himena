from pathlib import Path
from qtpy.QtCore import QPoint
from pytestqt.qtbot import QtBot
from himena.testing import WidgetTester
from himena_builtins.qt.widgets import QIpynbEdit
from himena_builtins._io import default_text_reader

def test_ipynb_widget(qtbot: QtBot, sample_dir: Path):
    ipynb_widget = QIpynbEdit()
    ipynb_widget.show()
    qtbot.addWidget(ipynb_widget)
    with WidgetTester(ipynb_widget) as tester:
        model = default_text_reader(sample_dir / "ipynb.ipynb")
        tester.update_model(model)
        tester.cycle_model()
        output_widget = ipynb_widget._cell_widgets[0]._output_widget
        assert output_widget is not None
        output_widget._make_contextmenu(QPoint(100, 100))
        control = ipynb_widget.control_widget()
        control._insert_code()
        control._insert_md()
        control._delete_cell()
        control._clear_outputs()

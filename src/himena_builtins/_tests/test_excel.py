import numpy as np
from pytestqt.qtbot import QtBot
from himena import MainWindow, StandardType
from himena.testing import WidgetTester
from himena_builtins.qt.widgets import QExcelEdit

def test_excel_widget(qtbot: QtBot):
    with WidgetTester(QExcelEdit()) as tester:
        qtbot.addWidget(tester.widget)
        tester.widget.show()
        tester.update_model(
            value={
                "sheet-0": {"a": [1, 2]},
                "sheet-1": {"a": [3, 4], "b": [5, 4]},
            },
        )
        old, new = tester.cycle_model()
        assert list(old.value.keys()) == list(new.value.keys())
        assert all(np.all(a == b) for a, b in zip(old.value.values(), new.value.values()))
        tester.widget.add_new_tab()
        assert tester.widget.count() == 3
        tester.drop_model(
            value={
                "sheet-10": {"a": [1, 2]},
                "sheet-11": [[1, 2], ["g", "g"]],
            },
            type=StandardType.EXCEL,
        )
        assert tester.widget.count() == 5
        tester.drop_model(
            value={
                "sheet-0": {"a": [1, 2]},
            },
            type=StandardType.TABLE,
        )
        assert tester.widget.count() == 6

        control = tester.widget.control_widget()
        control._value_line_edit.setText("abc")

def test_command(himena_ui: MainWindow):
    himena_ui.add_object({"sheet-0": [[1, 2], [3, 4]]}, type=StandardType.EXCEL)
    himena_ui.exec_action("builtins:duplicate-sheet-as-table")
    assert himena_ui.current_model.type == StandardType.TABLE
    val = himena_ui.current_model.value
    assert val.tolist() == [["1", "2"], ["3", "4"]]

import numpy as np
from pytestqt.qtbot import QtBot
from himena import MainWindow, StandardType
from himena.testing import WidgetTester
from himena_builtins.qt.stack import QExcelEdit, QDataFrameStack, QArrayStack

def test_excel_widget(qtbot: QtBot, himena_ui: MainWindow):
    # himena_ui is needed because drop_model needs current instance
    excel_edit = QExcelEdit(himena_ui)
    with WidgetTester(excel_edit) as tester:
        qtbot.addWidget(excel_edit)
        excel_edit.show()
        tester.update_model(
            value={
                "sheet-0": {"a": [1, 2]},
                "sheet-1": {"a": [3, 4], "b": [5, 4]},
            },
        )
        old, new = tester.cycle_model()
        assert list(old.value.keys()) == list(new.value.keys())
        assert all(np.all(a == b) for a, b in zip(old.value.values(), new.value.values()))
        excel_edit.add_new_tab()
        assert excel_edit.count() == 3
        tester.drop_model(
            value={
                "sheet-10": {"a": [1, 2]},
                "sheet-11": [[1, 2], ["g", "g"]],
            },
            type=StandardType.EXCEL,
        )
        assert excel_edit.count() == 5
        tester.drop_model(
            value={"a": [1, 2]},
            type=StandardType.TABLE,
        )
        assert excel_edit.count() == 6

        control = tester.widget.control_widget()
        control._value_line_edit.setText("abc")
        control.update_for_editing()
        control._insert_row_above()
        control._insert_row_below()
        control._insert_column_right()
        control._insert_column_left()
        control._remove_selected_rows()
        control._remove_selected_columns()
        control._auto_resize_columns()
        control._sort_table_by_column()

    tabbar = excel_edit.tabBar()
    excel_edit.setCurrentIndex(0)
    tabbar._make_drag()

def test_dataframe_dict(himena_ui: MainWindow, qtbot: QtBot):
    widget = QDataFrameStack(himena_ui)
    with WidgetTester(widget) as tester:
        qtbot.addWidget(widget)
        widget.show()
        tester.update_model(
            value={
                "sheet-0": {"a": [1, 2]},
                "sheet-1": {"a": [3, 4], "b": [5, 4]},
            },
        )
        tester.cycle_model()
        tester.widget.control_widget()

def test_array_dict(himena_ui: MainWindow, qtbot: QtBot):
    widget = QArrayStack(himena_ui)
    with WidgetTester(widget) as tester:
        qtbot.addWidget(widget)
        widget.show()
        tester.update_model(
            value={
                "sheet-0": np.array([[1, 2], [3, 4]]),
                "sheet-1": np.array([[5, 6], [7, 8]]),
            },
        )
        tester.cycle_model()
        tester.widget.control_widget()

def test_command(himena_ui: MainWindow):
    himena_ui.add_object({"sheet-0": [[1, 2], [3, 4]]}, type=StandardType.EXCEL)
    himena_ui.exec_action("builtins:dict:duplicate-tab")
    assert himena_ui.current_model.type == StandardType.TABLE
    val = himena_ui.current_model.value
    assert val.tolist() == [["1", "2"], ["3", "4"]]

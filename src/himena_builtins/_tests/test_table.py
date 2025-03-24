from numpy.testing import assert_equal
from pytestqt.qtbot import QtBot
from himena import MainWindow
from himena.standards.model_meta import TableMeta
from himena.testing import WidgetTester, table
from himena.types import WidgetDataModel
from himena_builtins.qt.widgets.table import QSpreadsheet
from qtpy.QtCore import Qt

_Ctrl = Qt.KeyboardModifier.ControlModifier


def test_table_edit(qtbot: QtBot):
    with _get_tester() as tester:
        tester.update_model(value=[["a", "b"], [0, 1]])
        tester.cycle_model()
        qtbot.addWidget(tester.widget)
        tester.widget.selection_model.current_index = (2, 3)
        tester.widget.model().setData(
            tester.widget.model().index(2, 3), "a", Qt.ItemDataRole.EditRole
        )
        assert tester.widget.to_model().value[2, 3] == "a"
        tester.widget.undo()
        tester.widget.redo()
        tester.widget._make_context_menu()
        qtbot.keyClick(tester.widget, Qt.Key.Key_A, modifier=_Ctrl)
        qtbot.keyClick(tester.widget, Qt.Key.Key_C, modifier=_Ctrl)
        qtbot.keyClick(tester.widget, Qt.Key.Key_X, modifier=_Ctrl)
        qtbot.keyClick(tester.widget, Qt.Key.Key_V, modifier=_Ctrl)
        qtbot.keyClick(tester.widget, Qt.Key.Key_Delete)
        qtbot.keyClick(tester.widget, Qt.Key.Key_F, modifier=_Ctrl)
        tester.widget.resize(100, 100)
        tester.widget._insert_row_above()
        tester.widget.undo()
        tester.widget.redo()
        tester.widget._insert_row_below()
        tester.widget.undo()
        tester.widget.redo()
        tester.widget._insert_column_left()
        tester.widget.undo()
        tester.widget.redo()
        tester.widget._insert_column_right()
        tester.widget.undo()
        tester.widget.redo()
        tester.widget.selection_model.current_index = (1, 1)
        tester.widget._remove_selected_rows()
        tester.widget.undo()
        tester.widget.redo()
        tester.widget.selection_model.current_index = (1, 1)
        tester.widget._remove_selected_columns()
        tester.widget.undo()
        tester.widget.redo()
        qtbot.keyClick(tester.widget, Qt.Key.Key_Z, modifier=_Ctrl)
        qtbot.keyClick(tester.widget, Qt.Key.Key_Y, modifier=_Ctrl)

def test_moving_in_table(qtbot: QtBot):
    with _get_tester() as tester:
        qtbot.addWidget(tester.widget)
        tester.widget.show()
        tester.update_model(value=[["a", "b"], ["c", "bc"]])
        tester.cycle_model()
        qtbot.addWidget(tester.widget)
        tester.widget.selection_model.current_index = (0, 0)
        qtbot.keyClick(tester.widget, Qt.Key.Key_Right)
        qtbot.keyClick(tester.widget, Qt.Key.Key_Left)
        qtbot.keyClick(tester.widget, Qt.Key.Key_Down)
        qtbot.keyClick(tester.widget, Qt.Key.Key_Up)
        qtbot.keyClick(tester.widget, Qt.Key.Key_Right, modifier=_Ctrl)
        qtbot.keyClick(tester.widget, Qt.Key.Key_Left, modifier=_Ctrl)
        qtbot.keyClick(tester.widget, Qt.Key.Key_Down, modifier=_Ctrl)
        qtbot.keyClick(tester.widget, Qt.Key.Key_Up, modifier=_Ctrl)
        qtbot.keyClick(tester.widget, Qt.Key.Key_Home)
        qtbot.keyClick(tester.widget, Qt.Key.Key_End)
        qtbot.keyClick(tester.widget, Qt.Key.Key_PageUp)
        qtbot.keyClick(tester.widget, Qt.Key.Key_PageDown)

def test_find_table(qtbot: QtBot):
    with _get_tester() as tester:
        tester.update_model(value=[["a", "b"], ["c", "bc"]])
        tester.cycle_model()
        qtbot.addWidget(tester.widget)
        qtbot.keyClick(tester.widget, Qt.Key.Key_F, modifier=_Ctrl)
        finder = tester.widget._finder_widget
        assert finder is not None
        finder._line_edit.setText("b")
        qtbot.keyClick(finder, Qt.Key.Key_Enter)
        qtbot.keyClick(finder, Qt.Key.Key_Enter, modifier=Qt.KeyboardModifier.ShiftModifier)
        finder._btn_next.click()
        finder._btn_prev.click()

def test_table_view_accepts_table_like(qtbot):
    table.test_accepts_table_like(_get_tester())

def test_table_view_current_position(qtbot):
    table.test_current_position(_get_tester())

def test_table_view_selections(qtbot):
    table.test_selections(_get_tester())

def test_copy_and_paste(qtbot):
    tester = _get_tester()
    qtbot.addWidget(tester.widget)
    tester.update_model(value=[["a", "b"], ["c", "bc"]])
    tester.widget.selection_model.current_index = (0, 0)
    tester.widget.selection_model.set_ranges([(slice(0, 1), slice(0, 1))])
    tester.widget._copy_as_csv()
    tester.widget._copy_as_markdown()
    tester.widget._copy_as_html()
    tester.widget._copy_as_rst()
    tester.widget._copy_to_clipboard()
    tester.widget.selection_model.current_index = (1, 1)
    tester.widget.selection_model.set_ranges([(slice(1, 2), slice(1, 2))])
    tester.widget._paste_from_clipboard()
    assert_equal(tester.widget.to_model().value, [["a", "b"], ["c", "a"]])
    tester.widget.selection_model.set_ranges([(slice(0, 2), slice(0, 3))])
    tester.widget._paste_from_clipboard()
    assert_equal(tester.widget.to_model().value, [["a", "a", "a"], ["a", "a", "a"]])
    tester.update_model(value=[["a", "b"], ["c", "bc"]])
    tester.widget.selection_model.set_ranges([(slice(0, 2), slice(0, 1))])
    tester.widget._copy_to_clipboard()
    tester.widget.selection_model.set_ranges([(slice(0, 2), slice(1, 2))])
    tester.widget._paste_from_clipboard()
    assert_equal(tester.widget.to_model().value, [["a", "a"], ["c", "c"]])

def _get_tester():
    return WidgetTester(QSpreadsheet())

def test_commands(himena_ui: MainWindow):
    model = WidgetDataModel(
        value=[["a", "b", "c"], ["d", "e", "f"]],
        type="table",
        metadata=TableMeta(selections=[], separator="\t")
    )
    himena_ui.add_data_model(model)
    himena_ui.exec_action("builtins:table:copy-as-csv")
    model = WidgetDataModel(
        value=[["a", "b", "c"], ["d", "e", "f"]],
        type="table",
        metadata=TableMeta(selections=[((0, 1), (1, 2))], separator=",")
    )
    himena_ui.add_data_model(model)
    himena_ui.exec_action("builtins:table:copy-as-csv")
    himena_ui.exec_action("builtins:table:copy-as-markdown")
    himena_ui.exec_action("builtins:table:copy-as-html")
    himena_ui.exec_action("builtins:table:copy-as-rst")
    himena_ui.exec_action("builtins:table:crop")
    himena_ui.exec_action("builtins:table:change-separator", with_params={"separator": "\t"})
    himena_ui.exec_action(
        "builtins:table:insert-incrementing-numbers",
        with_params={"selection": ((0, 1), (1, 4)), "start": 1, "step": 2}
    )
    assert_equal(himena_ui.current_model.value[0, 1:4], ["1", "3", "5"])
    himena_ui.exec_action(
        "builtins:table:insert-incrementing-numbers",
        with_params={"selection": ((0, 10), (1, 2)), "start": 1, "step": 1}
    )
    assert_equal(himena_ui.current_model.value[0:10, 1], [str(i) for i in range(1, 11)])

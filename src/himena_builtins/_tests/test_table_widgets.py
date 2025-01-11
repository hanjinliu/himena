from pytestqt.qtbot import QtBot
from himena.testing import WidgetTester, table
from himena_builtins.qt.widgets.table import QSpreadsheet
from qtpy.QtCore import Qt

_Ctrl = Qt.KeyboardModifier.ControlModifier


def test_table_edit(qtbot: QtBot):
    with _get_tester() as tester:
        tester.update_model(value=[["a", "b"], [0, 1]])
        tester.cycle_model()
        qtbot.addWidget(tester.widget)
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

def _get_tester():
    return WidgetTester(QSpreadsheet())

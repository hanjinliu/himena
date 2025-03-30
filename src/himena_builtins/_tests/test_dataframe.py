import numpy as np
import pytest
from qtpy.QtCore import Qt
from himena import MainWindow
from himena.testing.subwindow import WidgetTester
from himena_builtins.qt.widgets import QDataFrameView, QDataFramePlotView
import pandas as pd
import polars as pl
from pytestqt.qtbot import QtBot

_Ctrl = Qt.KeyboardModifier.ControlModifier

@pytest.mark.parametrize(
    "df",
    [
        {"a": [1, -2], "b": [3.0, -4.0], "str": ["a", "b"]},
        {"a": [3], "b": ["ggg"]},
        pd.DataFrame({"a": [1, -2], "b": [3.0, -4.0], "str": ["a", "b"]}),
        pl.DataFrame({"a": [1, -2], "b": [3.0, -4.0], "str": ["a", "b"]}),
    ],
)
def test_dataframe(qtbot: QtBot, df):
    with WidgetTester(QDataFrameView()) as tester:
        tester.update_model(value=df)
        qtbot.addWidget(tester.widget)
        table = tester.widget
        table.selection_model.set_ranges([(slice(1, 2), slice(1, 3))])
        table.copy_data()
        table._make_context_menu()
        table.model().headerData(0, Qt.Orientation.Horizontal, Qt.ItemDataRole.ToolTipRole)
        table.model().headerData(0, Qt.Orientation.Vertical, Qt.ItemDataRole.ToolTipRole)
        qtbot.keyClick(tester.widget, Qt.Key.Key_F, modifier=_Ctrl)
        finder = tester.widget._finder_widget
        assert finder is not None
        finder._line_edit.setText("b")
        qtbot.keyClick(finder, Qt.Key.Key_Enter)
        qtbot.keyClick(finder, Qt.Key.Key_Enter, modifier=Qt.KeyboardModifier.ShiftModifier)
        assert type(tester.to_model().value) is type(df)
        tester.is_modified()
        assert tester.widget._hor_header._data_model_for_drag() is not None

def test_dataframe_plot(qtbot: QtBot):
    x = np.linspace(0, 3, 20)
    df = {"x": x, "y": np.sin(x * 2), "z": np.cos(x * 2)}
    with WidgetTester(QDataFramePlotView()) as tester:
        tester.update_model(value=df)
        tester.cycle_model()
        qtbot.addWidget(tester.widget)

def test_dataframe_command(himena_ui: MainWindow):
    win = himena_ui.add_object({"a": [1, 2], "b": ["p", "q"]}, type="dataframe")
    himena_ui.exec_action("builtins:dataframe:header-to-row")
    himena_ui.current_window = win
    himena_ui.exec_action("builtins:dataframe:series-as-array", with_params={"column": "a"})
    himena_ui.current_window = win
    himena_ui.exec_action("builtins:dataframe:select-columns-by-name", with_params={"columns": ["b"]})
    assert _data_frame_equal(himena_ui.current_model.value, {"b": ["p", "q"]})
    himena_ui.current_window = win
    himena_ui.exec_action("builtins:dataframe:filter", with_params={"column": "b", "operator": "eq", "value": "p"})
    assert _data_frame_equal(himena_ui.current_model.value, {"a": [1], "b": ["p"]})
    himena_ui.current_window = win
    himena_ui.exec_action("builtins:dataframe:sort", with_params={"column": "b", "descending": True})
    assert _data_frame_equal(himena_ui.current_model.value, {"a": [2, 1], "b": ["q", "p"]})

def _data_frame_equal(a: dict, b: dict):
    for k in a.keys():
        if not np.all(a[k] == b[k]):
            return False
    return True

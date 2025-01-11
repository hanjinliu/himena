import numpy as np
import pytest
from qtpy.QtCore import Qt
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
        pd.DataFrame({"a": [1, -2], "b": [3.0, -4.0], "str": ["a", "b"]}),
        pl.DataFrame({"a": [1, -2], "b": [3.0, -4.0], "str": ["a", "b"]}),
    ],
)
def test_dataframe(qtbot: QtBot, df):
    with WidgetTester(QDataFrameView()) as tester:
        tester.update_model(value=df)
        qtbot.addWidget(tester.widget)
        qtbot.keyClick(tester.widget, Qt.Key.Key_F, modifier=_Ctrl)
        finder = tester.widget._finder_widget
        assert finder is not None
        finder._line_edit.setText("b")
        qtbot.keyClick(finder, Qt.Key.Key_Enter)
        qtbot.keyClick(finder, Qt.Key.Key_Enter, modifier=Qt.KeyboardModifier.ShiftModifier)
        assert type(tester.to_model().value) is type(df)
        tester.is_modified()

def test_dataframe_plot(qtbot: QtBot):
    x = np.linspace(0, 3, 20)
    df = {"x": x, "y": np.sin(x * 2), "z": np.cos(x * 2)}
    with WidgetTester(QDataFramePlotView()) as tester:
        tester.update_model(value=df)
        tester.cycle_model()
        qtbot.addWidget(tester.widget)

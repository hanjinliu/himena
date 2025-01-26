import numpy as np
from numpy.testing import assert_array_equal
from qtpy.QtCore import Qt
from pytestqt.qtbot import QtBot
from himena import MainWindow, StandardType
from himena.standards.model_meta import ArrayMeta, ArrayAxis
from himena.testing import WidgetTester
from himena_builtins.qt.widgets import QArrayView

_Ctrl = Qt.KeyboardModifier.ControlModifier

def test_array_view(qtbot: QtBot):
    with WidgetTester(QArrayView()) as tester:
        qtbot.addWidget(tester.widget)
        tester.update_model(value=np.arange(72).reshape(3, 2, 3, 4))
        assert len(tester.widget._spinboxes) == 2
        assert tester.widget._spinboxes[0].maximum() == 2
        assert tester.widget._spinboxes[1].maximum() == 1
        tester.widget._spinboxes[0].setValue(1)
        tester.widget._spinboxes[0].setValue(2)
        tester.widget._spinboxes[1].setValue(1)
        tester.widget._spinboxes[1].setValue(0)
        tester.widget.selection_model.set_ranges([(slice(1, 2), slice(1, 3))])
        qtbot.keyClick(tester.widget, Qt.Key.Key_C, _Ctrl)
        old, new = tester.cycle_model()
        assert np.all(old.value == new.value)
        assert new.metadata.selections == [((1, 2), (1, 3))]
        assert old.metadata.selections == new.metadata.selections

def test_structured(qtbot: QtBot):
    with WidgetTester(QArrayView()) as tester:
        qtbot.addWidget(tester.widget)
        tester.update_model(
            value=np.array(
                [("a", 1, 2.3, True), ("b", -2, -0.04, False)],
                dtype=[("name", "U1"), ("value", "i4"), ("float", "f4"), ("b", "bool")]
            )
        )
        assert tester.to_model().value.shape == (2,)
        assert tester.to_model().value.dtype.names == ("name", "value", "float", "b")

        tester.widget.selection_model.set_ranges([(slice(1, 2), slice(1, 3))])
        qtbot.keyClick(tester.widget, Qt.Key.Key_C, _Ctrl)
        old, new = tester.cycle_model()
        assert np.all(old.value == new.value)
        assert new.metadata.selections == [((1, 2), (1, 3))]
        assert old.metadata.selections == new.metadata.selections


def test_binary_operations(himena_ui: MainWindow):
    win = himena_ui.add_object(np.arange(24).reshape(2, 3, 4), type=StandardType.ARRAY)
    model = win.to_model()
    himena_ui.exec_action(
        "builtins:binary-operation",
        with_params={"x": model, "y": model, "operation": "sub", "result_dtype": "input"},
    )
    himena_ui.exec_action(
        "builtins:binary-operation",
        with_params={"x": model, "y": model, "operation": "sub", "result_dtype": "float32"}
    )
    himena_ui.exec_action(
        "builtins:binary-operation",
        with_params={"x": model, "y": model, "operation": "sub", "result_dtype": "float64"}
    )


def test_array_commands(himena_ui: MainWindow):
    win = himena_ui.add_object(np.arange(24).reshape(2, 3, 4), type=StandardType.ARRAY)
    himena_ui.exec_action("builtins:array-duplicate-slice")
    assert himena_ui.current_model.value.shape == (3, 4)
    assert_array_equal(himena_ui.current_model.value, np.arange(12).reshape(3, 4))

    himena_ui.add_object(np.arange(24).reshape(2, 3, 4), type=StandardType.IMAGE)
    himena_ui.exec_action("builtins:array-duplicate-slice")
    assert himena_ui.current_model.value.shape == (3, 4)
    assert_array_equal(himena_ui.current_model.value, np.arange(12).reshape(3, 4))

    himena_ui.current_window = win
    win.update_model(
        win.to_model().with_metadata(
            ArrayMeta(
                axes=[ArrayAxis(name=name) for name in ("t", "y", "x")],
                selections=[((1, 2), (1, 3))],
            )
        )
    )
    himena_ui.exec_action("builtins:crop-array")
    assert himena_ui.current_model.value.shape == (2, 1, 2)
    himena_ui.current_window = win
    himena_ui.exec_action(
        "builtins:crop-array-nd", with_params={
            "axis_0": (0, 1),
            "axis_1": (1, 2),
            "axis_2": (0, 2),
        }
    )
    assert himena_ui.current_model.value.shape == (1, 1, 2)

    himena_ui.exec_action("builtins:array-astype", with_params={"dtype": "float32"})
    himena_ui.current_window = win
    himena_ui.exec_action(
        "builtins:set-array-scale",
        with_params={"axis_2": "1.4", "axis_1": "1.0 um", "axis_0": "0.5um"}
    )

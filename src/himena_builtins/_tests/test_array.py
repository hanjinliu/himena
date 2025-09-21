from typing import Sequence
from cmap import Colormap
import numpy as np
from numpy.testing import assert_array_equal
import pytest
from pytestqt.qtbot import QtBot
from qtpy.QtCore import Qt
from qtpy import QtWidgets as QtW
from himena import MainWindow, StandardType
from himena.standards.model_meta import ArrayMeta, DimAxis, ImageChannel, ImageMeta
from himena.testing import WidgetTester
from himena_builtins.qt.array import QArrayView
from himena_builtins.tools.array import _broadcast_arrays

_Ctrl = Qt.KeyboardModifier.ControlModifier

def test_array_view(himena_ui: MainWindow, qtbot: QtBot):
    with WidgetTester(QArrayView(himena_ui)) as tester:
        qtbot.addWidget(tester.widget)
        tester.widget.show()
        table = tester.widget._table
        table.update()
        table.model().data(table.model().index(0, 0), Qt.ItemDataRole.ToolTipRole)
        table.model().headerData(0, Qt.Orientation.Horizontal, Qt.ItemDataRole.ToolTipRole)
        table.model().headerData(0, Qt.Orientation.Vertical, Qt.ItemDataRole.ToolTipRole)
        table.selection_model.set_ranges([(slice(1, 2), slice(1, 3))])
        table._copy_data()
        table._make_context_menu()
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

def test_structured(himena_ui: MainWindow, qtbot: QtBot):
    with WidgetTester(QArrayView(himena_ui)) as tester:
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

def test_copy_and_paste(himena_ui: MainWindow, qtbot: QtBot):
    with WidgetTester(QArrayView(himena_ui)) as tester:
        qtbot.addWidget(tester.widget)
        tester.update_model(value=np.zeros((3, 5, 3, 4), dtype=np.int32))
        tester.widget.set_indices(1, 2)
        tester.widget.selection_model.current_index = (2, 0)
        qtbot.keyClick(tester.widget._table, Qt.Key.Key_F2)
        tester.widget._table.set_string_input(2, 0, "4")
        assert tester.to_model().value[1, 2, 2, 0] == 4
        # test copy and paste
        tester.widget.selection_model.set_ranges([(slice(2, 3), slice(0, 1))])
        tester.widget._table._copy_data()
        QtW.QApplication.processEvents()
        assert QtW.QApplication.clipboard().text() == "4"
        tester.widget.selection_model.set_ranges([(slice(0, 2), slice(1, 3))])
        tester.widget._table._paste_from_clipboard()
        assert_array_equal(tester.to_model().value[1, 2, 0:2, 1:3], 4)
        QtW.QApplication.clipboard().setText("1\t2\n3\t4")
        QtW.QApplication.processEvents()
        tester.widget.selection_model.set_ranges([(slice(0, 1), slice(0, 1))])
        tester.widget._table._paste_from_clipboard()
        assert_array_equal(tester.to_model().value[1, 2, 0:2, 0:2], [[1, 2], [3, 4]])

def test_binary_operations(himena_ui: MainWindow):
    win = himena_ui.add_object(np.arange(24, dtype=np.uint16).reshape(2, 3, 4), type=StandardType.ARRAY)
    model = win.to_model()
    himena_ui.exec_action(
        "builtins:array:binary-operation",
        with_params={"x": model, "y": model, "operation": "sub", "result_dtype": "input"},
    )
    himena_ui.exec_action(
        "builtins:array:binary-operation",
        with_params={"x": model, "y": model, "operation": "sub", "result_dtype": "float32"}
    )
    himena_ui.exec_action(
        "builtins:array:binary-operation",
        with_params={"x": model, "y": model, "operation": "sub", "result_dtype": "float64"}
    )


def test_array_commands(himena_ui: MainWindow):
    win = himena_ui.add_object(np.arange(24).reshape(2, 3, 4), type=StandardType.ARRAY)
    himena_ui.exec_action("builtins:array:duplicate-slice")
    assert himena_ui.current_model.value.shape == (3, 4)
    assert_array_equal(himena_ui.current_model.value, np.arange(12).reshape(3, 4))

    himena_ui.add_object(
        np.arange(24).reshape(2, 3, 4),
        type=StandardType.IMAGE,
        metadata=ImageMeta(
            channel_axis=0,
            channels=[ImageChannel(colormap="red"), ImageChannel(colormap="green")],
        )
    )
    himena_ui.exec_action("builtins:array:duplicate-slice")
    assert himena_ui.current_model.value.shape == (3, 4)
    assert himena_ui.current_model.metadata.channel_axis is None
    assert himena_ui.current_model.metadata.channels[0].colormap == Colormap("red")
    assert_array_equal(himena_ui.current_model.value, np.arange(12).reshape(3, 4))

    himena_ui.current_window = win
    win.update_model(
        win.to_model().with_metadata(
            ArrayMeta(
                axes=_make_axes("tyx"),
                selections=[((1, 2), (1, 3))],
            )
        )
    )
    himena_ui.exec_action("builtins:array:crop")
    assert himena_ui.current_model.value.shape == (2, 1, 2)
    himena_ui.current_window = win
    himena_ui.exec_action(
        "builtins:array:crop-nd", with_params={
            "axis_0": (0, 1),
            "axis_1": (1, 2),
            "axis_2": (0, 2),
        }
    )
    assert himena_ui.current_model.value.shape == (1, 1, 2)

    himena_ui.exec_action("builtins:array:astype", with_params={"dtype": "float32"})
    himena_ui.current_window = win
    himena_ui.exec_action(
        "builtins:array:set-scale",
        with_params={"axis_2": "1.4", "axis_1": "1.0 um", "axis_0": "0.5um"}
    )
    meta_new = win.to_model().metadata
    assert isinstance(meta_new, ArrayMeta)
    meta_new.axes[0].scale == pytest.approx(0.5)
    meta_new.axes[0].unit == "um"
    meta_new.axes[1].scale == pytest.approx(1.0)
    meta_new.axes[1].unit == "um"
    meta_new.axes[2].scale == pytest.approx(1.4)
    meta_new.axes[2].unit == ""
    himena_ui.exec_action("builtins:array:with-axes", with_params={"axis_0": "t", "axis_1": "y", "axis_2": "x"})
    meta_new = win.to_model().metadata
    assert isinstance(meta_new, ArrayMeta)
    assert meta_new.axes[0].name == "t"
    assert meta_new.axes[1].name == "y"
    assert meta_new.axes[2].name == "x"

def test_copy_on_write(himena_ui: MainWindow, qtbot: QtBot):
    view = QArrayView(himena_ui)
    qtbot.addWidget(view)
    with WidgetTester(view) as tester:
        tester.update_model(value=np.zeros((3, 4)), type="array")

        array_orig = np.array([[1, 2], [3, 4]])
        tester.update_model(value=array_orig, type=StandardType.ARRAY)
        view.array_update((slice(0, 1), slice(1, 2)), 10)
        assert_array_equal(view.to_model().value, [[1, 10], [3, 4]])
        assert_array_equal(array_orig, [[1, 2], [3, 4]])

        view_other = QArrayView(himena_ui)
        view_other.update_model(view.to_model())
        view.array_update((slice(0, 1), slice(0, 1)), 20)
        assert_array_equal(view.to_model().value, [[20, 10], [3, 4]])
        assert_array_equal(view_other.to_model().value, [[1, 10], [3, 4]])

@pytest.mark.parametrize(
    "shape0, shape1, axes0, axes1, expected_shape, expected_axes",
    [
        ((2, 3), (2, 3), "yx", "yx", (2, 3), "yx"),
        ((2, 3), (3,), "yx", "x", (2, 3), "yx"),
        ((2,), (2, 3), "y", "yx", (2, 3), "yx"),
        ((2, 5, 4, 3), (2, 4, 3), "tzyx", "tyx", (2, 5, 4, 3), "tzyx"),
        ((5,), (2, 5), "t", None, (2, 5), None),
    ]
)
def test_broadcast_array(
    shape0: tuple[int, ...],
    shape1: tuple[int, ...],
    axes0: Sequence[str],
    axes1: Sequence[str],
    expected_shape: tuple[int, ...],
    expected_axes: Sequence[str],
):
    a_out, b_out, axes = _broadcast_arrays(
        np.zeros(shape0),
        np.zeros(shape1),
        _make_axes(axes0),
        _make_axes(axes1),
    )
    out = a_out + b_out
    assert out.shape == expected_shape
    if expected_axes is None:
        assert axes is None
    else:
        assert [a.name for a in axes] == list(expected_axes)

def _make_axes(names: Sequence[str] | None) -> list[DimAxis] | None:
    if names is None:
        return None
    return [DimAxis(name=name) for name in names]

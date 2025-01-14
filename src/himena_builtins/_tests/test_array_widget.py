import numpy as np
from qtpy.QtCore import Qt
from pytestqt.qtbot import QtBot
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

def test_structured(qtbot):
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
